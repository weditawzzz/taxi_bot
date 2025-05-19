from datetime import datetime, time
from config import Config


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
    """Рассчитывает стоимость поездки с учетом ночного тарифа"""
    if distance > Config.MAX_CITY_DISTANCE_KM:
        raise ValueError("Distance exceeds city limits")

    base = Config.TARIFFS["city"]["base"]
    per_km = Config.TARIFFS["city"]["per_km"]

    total = base + (distance * per_km)

    if is_night_tariff():
        total *= Config.TARIFFS["city"]["night_multiplier"]

    return round(total, 2)