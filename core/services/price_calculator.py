"""
Сервис для расчета стоимости поездок
"""
import logging
from decimal import Decimal
from typing import Optional
from datetime import datetime, time

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import config, Config  # Исправленный импорт
from ..exceptions import ValidationError, BusinessLogicError, ServiceError

logger = logging.getLogger(__name__)


def is_night_tariff() -> bool:
    """Проверяет, действует ли ночной тариф"""
    now = datetime.now().time()
    night_start, night_end = Config.TARIFFS["night_time"]

    # Ночной тариф действует с 22:00 до 06:00
    if night_start > night_end:  # Если период переходит через полночь
        return now >= night_start or now <= night_end
    else:
        return night_start <= now <= night_end


def calculate_city_price(distance: float) -> float:
    """Рассчитывает стоимость городской поездки с учетом ночного тарифа"""
    if distance > Config.MAX_CITY_DISTANCE_KM:
        raise ValueError("Distance exceeds city limits")

    base = Config.TARIFFS["city"]["base"]
    per_km = Config.TARIFFS["city"]["per_km"]

    total = base + (distance * per_km)

    if is_night_tariff():
        total *= Config.TARIFFS["city"]["night_multiplier"]

    return round(total, 2)


def calculate_alcohol_delivery_price(distance: float) -> float:
    """Рассчитывает стоимость доставки алкоголя из магазина"""
    base = Config.TARIFFS["alcohol_delivery"]["base"]
    per_km = Config.TARIFFS["alcohol_delivery"]["per_km"]
    service_fee = Config.TARIFFS["alcohol_delivery"]["service_fee"]

    total = base + service_fee + (distance * per_km)

    if is_night_tariff():
        total *= Config.TARIFFS["alcohol_delivery"]["night_multiplier"]

    return round(total, 2)


class PriceCalculatorService:
    """Сервис для расчета стоимости поездок"""

    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        self.base_price = Decimal(str(config.base_price_pln))
        self.price_per_km = Decimal(str(config.price_per_km_pln))

    def calculate_price(self, distance_km: float, duration_minutes: int = 0) -> Decimal:
        """Рассчитать стоимость поездки"""
        try:
            if distance_km < 0:
                raise ValidationError("Distance cannot be negative")

            if distance_km > config.max_ride_distance_km:
                raise BusinessLogicError(f"Distance exceeds maximum allowed: {config.max_ride_distance_km} km")

            distance_decimal = Decimal(str(distance_km))
            price = self.base_price + (distance_decimal * self.price_per_km)

            # Минимальная стоимость
            min_price = Decimal('5.00')
            price = max(price, min_price)

            # Доплата за время ожидания (если больше 30 минут)
            if duration_minutes > 30:
                extra_time = duration_minutes - 30
                time_surcharge = Decimal(str(extra_time)) * Decimal('0.20')  # 0.20 PLN за минуту
                price += time_surcharge

            # Округляем до 2 знаков после запятой
            return price.quantize(Decimal('0.01'))

        except (ValueError, TypeError) as e:
            logger.error(f"Invalid input for price calculation: {e}")
            raise ValidationError("Invalid distance or duration value")
        except Exception as e:
            logger.error(f"Error calculating price: {e}")
            raise ServiceError("Failed to calculate price")

    def apply_surge_pricing(self, base_price: Decimal, surge_multiplier: float = 1.0) -> Decimal:
        """Применить повышающий коэффициент (например, в час пик)"""
        try:
            if surge_multiplier < 1.0:
                raise ValidationError("Surge multiplier cannot be less than 1.0")

            multiplier = Decimal(str(surge_multiplier))
            return (base_price * multiplier).quantize(Decimal('0.01'))

        except (ValueError, TypeError) as e:
            logger.error(f"Invalid surge multiplier: {e}")
            raise ValidationError("Invalid surge multiplier")

    def get_price_breakdown(self, distance_km: float, duration_minutes: int = 0) -> dict:
        """Получить детальный расчет цены"""
        try:
            breakdown = {
                'base_price': self.base_price,
                'distance_km': distance_km,
                'distance_price': Decimal(str(distance_km)) * self.price_per_km,
                'time_surcharge': Decimal('0.00'),
                'total_price': Decimal('0.00')
            }

            # Расчет доплаты за время
            if duration_minutes > 30:
                extra_time = duration_minutes - 30
                breakdown['time_surcharge'] = Decimal(str(extra_time)) * Decimal('0.20')

            # Общая стоимость
            total = breakdown['base_price'] + breakdown['distance_price'] + breakdown['time_surcharge']
            breakdown['total_price'] = max(total, Decimal('5.00'))  # Минимум 5 PLN

            return breakdown

        except Exception as e:
            logger.error(f"Error calculating price breakdown: {e}")
            raise ServiceError("Failed to calculate price breakdown")


# Функции для обратной совместимости
def get_user_language(telegram_id: int) -> str:
    """Синхронная версия получения языка пользователя для совместимости"""
    return "pl"  # Fallback


async def get_user_language_async(telegram_id: int) -> str:
    """Асинхронная версия получения языка пользователя"""
    try:
        from .user_service import UserService
        user_service = UserService()
        user = await user_service.get_user_by_telegram_id(telegram_id)
        return user.language if user and user.language else "pl"
    except Exception:
        return "pl"