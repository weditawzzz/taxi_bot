"""
Унифицированная конфигурация с валидацией и типизацией
"""
from dataclasses import dataclass
from typing import Optional
import os
import sys
from pathlib import Path
import logging
from datetime import time

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    url: str
    echo: bool = False


@dataclass
class BotConfig:
    """Конфигурация бота"""
    token: str


@dataclass
class MapsConfig:
    """Конфигурация для карт и геолокации"""
    api_key: str
    default_city: str = "Szczecin"
    default_country: str = "Poland"


@dataclass
class TariffConfig:
    """Конфигурация тарифов"""
    # Городские поездки
    city_base: float = 10.0
    city_per_km: float = 3.0
    city_night_multiplier: float = 1.2

    # Аэропорт
    airport_goleniow: float = 170.0
    airport_berlin: float = 600.0
    airport_night_multiplier: float = 1.2

    # Доставка алкоголя
    alcohol_base: float = 25.0
    alcohol_per_km: float = 3.0
    alcohol_service_fee: float = 15.0
    alcohol_night_multiplier: float = 1.3

    # Междугородние
    intercity_base: float = 10.0
    intercity_per_km: float = 2.0
    intercity_night_multiplier: float = 1.2
    intercity_min_distance: float = 50.0

    # Международные
    international_base: float = 10.0
    international_per_km: float = 2.5
    international_night_multiplier: float = 1.2

    # Время ночного тарифа
    night_start: time = time(22, 0)
    night_end: time = time(6, 0)


@dataclass
class Config:
    """Главная конфигурация приложения"""
    # Боты
    client_bot: BotConfig
    driver_bot: BotConfig

    # База данных
    database: DatabaseConfig

    # Внешние сервисы
    maps: MapsConfig

    # Тарифы
    tariffs: TariffConfig

    # Общие настройки
    debug: bool = False
    log_level: str = "INFO"

    # Географические ограничения
    default_city: str = "Szczecin"
    max_city_distance_km: int = 25

    # Бизнес-логика
    max_ride_distance_km: int = 50
    base_price_pln: float = 5.0
    price_per_km_pln: float = 2.5

    # Водители
    driver_chat_id: str = "628521909"
    driver_ids: list = None

    @classmethod
    def from_env(cls, allow_missing_tokens: bool = False) -> 'Config':
        """Создание конфигурации из переменных окружения"""
        try:
            # Проверяем обязательные переменные
            client_token = os.getenv('CLIENT_BOT_TOKEN')
            driver_token = os.getenv('DRIVER_BOT_TOKEN')
            maps_key = os.getenv('MAPS_API_KEY', 'AIzaSyBHUFjfnp7oN4BC27_wlOuCqr33WOrNRQo')

            # Если токены отсутствуют и allow_missing_tokens=False
            if not allow_missing_tokens:
                if not client_token:
                    raise ValueError("CLIENT_BOT_TOKEN not found in environment")
                if not driver_token:
                    raise ValueError("DRIVER_BOT_TOKEN not found in environment")

            # Fallback токены для миграции
            if not client_token:
                client_token = "PLACEHOLDER_CLIENT_TOKEN"
            if not driver_token:
                driver_token = "PLACEHOLDER_DRIVER_TOKEN"

            # База данных
            db_url = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///data/database.db')
            database = DatabaseConfig(
                url=db_url,
                echo=os.getenv('DB_ECHO', 'false').lower() == 'true'
            )

            # Клиентский бот
            client_bot = BotConfig(token=client_token)

            # Водительский бот
            driver_bot = BotConfig(token=driver_token)

            # Карты
            maps = MapsConfig(
                api_key=maps_key,
                default_city=os.getenv('DEFAULT_CITY', 'Szczecin'),
                default_country=os.getenv('DEFAULT_COUNTRY', 'Poland')
            )

            # Тарифы
            tariffs = TariffConfig()

            # Водители
            driver_ids_str = os.getenv('DRIVER_IDS', '628521909,987654321')
            driver_ids = driver_ids_str.split(',') if driver_ids_str else ['628521909']

            return cls(
                client_bot=client_bot,
                driver_bot=driver_bot,
                database=database,
                maps=maps,
                tariffs=tariffs,
                debug=os.getenv('DEBUG', 'false').lower() == 'true',
                log_level=os.getenv('LOG_LEVEL', 'INFO'),
                max_ride_distance_km=int(os.getenv('MAX_RIDE_DISTANCE_KM', '50')),
                base_price_pln=float(os.getenv('BASE_PRICE_PLN', '5.0')),
                price_per_km_pln=float(os.getenv('PRICE_PER_KM_PLN', '2.5')),
                driver_chat_id=os.getenv('DRIVER_CHAT_ID', '628521909'),
                driver_ids=driver_ids
            )

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise


def setup_logging(config: Config) -> None:
    """Настройка логирования"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Создаем директорию для логов если её нет
    Path('logs').mkdir(exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/taxi_bot.log', encoding='utf-8')
        ]
    )


def is_night_tariff() -> bool:
    """Проверяет, действует ли ночной тариф"""
    from datetime import datetime
    now = datetime.now().time()
    night_start = config.tariffs.night_start
    night_end = config.tariffs.night_end

    # Ночной тариф действует с 22:00 до 06:00
    if night_start > night_end:  # Если период переходит через полночь
        return now >= night_start or now <= night_end
    else:
        return night_start <= now <= night_end


def calculate_city_price(distance: float) -> float:
    """Рассчитывает стоимость городской поездки с учетом ночного тарифа"""
    if distance > config.max_city_distance_km:
        raise ValueError("Distance exceeds city limits")

    base = config.tariffs.city_base
    per_km = config.tariffs.city_per_km

    total = base + (distance * per_km)

    if is_night_tariff():
        total *= config.tariffs.city_night_multiplier

    return round(total, 2)


def calculate_alcohol_delivery_price(distance: float) -> float:
    """Рассчитывает стоимость доставки алкоголя из магазина"""
    base = config.tariffs.alcohol_base
    per_km = config.tariffs.alcohol_per_km
    service_fee = config.tariffs.alcohol_service_fee

    total = base + service_fee + (distance * per_km)

    if is_night_tariff():
        total *= config.tariffs.alcohol_night_multiplier

    return round(total, 2)


# Определяем, идет ли миграция (по имени файла или переменной окружения)
is_migration = any([
    'migration' in sys.argv[0] if len(sys.argv) > 0 else False,
    os.getenv('MIGRATION_MODE', '').lower() == 'true'
])

# Глобальный экземпляр конфигурации
try:
    import sys
    config = Config.from_env(allow_missing_tokens=is_migration)

    # Настраиваем логирование при импорте, если не миграция
    if not is_migration:
        setup_logging(config)

except Exception as e:
    if is_migration:
        print(f"⚠️ Конфигурация загружена в режиме миграции: {e}")
        # Создаем минимальную конфигурацию для миграции
        config = None
    else:
        raise


# ============================================
# ОБРАТНАЯ СОВМЕСТИМОСТЬ СО СТАРЫМ config.py
# ============================================

class LegacyConfig:
    """Класс для обратной совместимости со старой конфигурацией"""

    def __init__(self, config_instance):
        if config_instance is None:
            # Fallback значения для миграции
            self.DEFAULT_CITY = "Szczecin"
            self.GOOGLE_MAPS_API_KEY = "AIzaSyBHUFjfnp7oN4BC27_wlOuCqr33WOrNRQo"
            self.MAX_CITY_DISTANCE_KM = 25
            self.DRIVER_CHAT_ID = "628521909"
            self.CLIENT_BOT_TOKEN = "PLACEHOLDER_CLIENT_TOKEN"
            self.DRIVER_BOT_TOKEN = "PLACEHOLDER_DRIVER_TOKEN"
            self.DRIVER_IDS = ['628521909', '6158974369']

            self.TARIFFS = {
                "city": {"base": 10.0, "per_km": 3.0, "night_multiplier": 1.2},
                "airport": {"goleniow": 170.0, "berlin": 600.0, "night_multiplier": 1.2},
                "night_time": (time(22, 0), time(6, 0)),
                "alcohol_delivery": {"base": 25.0, "per_km": 3.0, "night_multiplier": 1.3, "service_fee": 15.0},
                "intercity": {"base": 10.0, "per_km": 2.0, "night_multiplier": 1.2, "min_distance": 50.0},
                "international": {"base": 10.0, "per_km": 2.5, "night_multiplier": 1.2}
            }
            self.NIGHT_HOURS = (time(22, 0), time(6, 0))
        else:
            # Нормальная конфигурация
            self.DEFAULT_CITY = config_instance.default_city
            self.GOOGLE_MAPS_API_KEY = config_instance.maps.api_key
            self.MAX_CITY_DISTANCE_KM = config_instance.max_city_distance_km

            self.TARIFFS = {
                "city": {
                    "base": config_instance.tariffs.city_base,
                    "per_km": config_instance.tariffs.city_per_km,
                    "night_multiplier": config_instance.tariffs.city_night_multiplier
                },
                "airport": {
                    "goleniow": config_instance.tariffs.airport_goleniow,
                    "berlin": config_instance.tariffs.airport_berlin,
                    "night_multiplier": config_instance.tariffs.airport_night_multiplier
                },
                "night_time": (config_instance.tariffs.night_start, config_instance.tariffs.night_end),
                "alcohol_delivery": {
                    "base": config_instance.tariffs.alcohol_base,
                    "per_km": config_instance.tariffs.alcohol_per_km,
                    "night_multiplier": config_instance.tariffs.alcohol_night_multiplier,
                    "service_fee": config_instance.tariffs.alcohol_service_fee
                },
                "intercity": {
                    "base": config_instance.tariffs.intercity_base,
                    "per_km": config_instance.tariffs.intercity_per_km,
                    "night_multiplier": config_instance.tariffs.intercity_night_multiplier,
                    "min_distance": config_instance.tariffs.intercity_min_distance
                },
                "international": {
                    "base": config_instance.tariffs.international_base,
                    "per_km": config_instance.tariffs.international_per_km,
                    "night_multiplier": config_instance.tariffs.international_night_multiplier
                }
            }

            self.NIGHT_HOURS = (config_instance.tariffs.night_start, config_instance.tariffs.night_end)
            self.DRIVER_CHAT_ID = config_instance.driver_chat_id
            self.CLIENT_BOT_TOKEN = config_instance.client_bot.token
            self.DRIVER_BOT_TOKEN = config_instance.driver_bot.token
            self.DRIVER_IDS = config_instance.driver_ids


# Создаем экземпляр для обратной совместимости
Config = LegacyConfig(config)