"""
Улучшенная конфигурация с валидацией и типизацией
"""
from dataclasses import dataclass
from typing import Optional
import os
from pathlib import Path
import logging

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
class Config:
    """Главная конфигурация приложения"""
    # Боты
    client_bot: BotConfig
    driver_bot: BotConfig

    # База данных
    database: DatabaseConfig

    # Внешние сервисы
    maps: MapsConfig

    # Общие настройки
    debug: bool = False
    log_level: str = "INFO"

    # Бизнес-логика
    max_ride_distance_km: int = 50
    base_price_pln: float = 5.0
    price_per_km_pln: float = 2.5

    @classmethod
    def from_env(cls) -> 'Config':
        """Создание конфигурации из переменных окружения"""
        try:
            # Проверяем обязательные переменные
            client_token = os.getenv('CLIENT_BOT_TOKEN')
            driver_token = os.getenv('DRIVER_BOT_TOKEN')
            maps_key = os.getenv('MAPS_API_KEY', 'test_key')  # Для тестов

            if not client_token:
                raise ValueError("CLIENT_BOT_TOKEN not found in environment")
            if not driver_token:
                raise ValueError("DRIVER_BOT_TOKEN not found in environment")

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

            return cls(
                client_bot=client_bot,
                driver_bot=driver_bot,
                database=database,
                maps=maps,
                debug=os.getenv('DEBUG', 'false').lower() == 'true',
                log_level=os.getenv('LOG_LEVEL', 'INFO'),
                max_ride_distance_km=int(os.getenv('MAX_RIDE_DISTANCE_KM', '50')),
                base_price_pln=float(os.getenv('BASE_PRICE_PLN', '5.0')),
                price_per_km_pln=float(os.getenv('PRICE_PER_KM_PLN', '2.5'))
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


# Глобальный экземпляр конфигурации
config = Config.from_env()

# Настраиваем логирование при импорте
setup_logging(config)