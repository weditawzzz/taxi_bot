from datetime import time


class Config:
    # Тарифы (всё в zł)
    DEFAULT_CITY = "Szczecin"  # Добавляем город по умолчанию
    GOOGLE_MAPS_API_KEY = "AIzaSyBHUFjfnp7oN4BC27_wlOuCqr33WOrNRQo"  # Замените на реальный ключ
    MAX_CITY_DISTANCE_KM = 25
    TARIFFS = {
        "city": {"base": 10, "per_km": 3, "night_multiplier": 1.2},
        "airport": {
            "goleniow": 170,
            "berlin": 600,
            "night_multiplier": 1.2
        },
        "night_time": (time(22, 0), time(6, 0)),  # Используем time() вместо строк
        "alcohol": {"base": 10, "per_km": 2, "night_multiplier": 1.2},
        "intercity": {"base": 10, "per_km": 2, "night_multiplier": 1.2, "min_distance": 50},
        "international": {"base": 10, "per_km": 2.5, "night_multiplier": 1.2}
    }

    # Время ночного тарифа
    NIGHT_HOURS = (time(22, 0), time(6, 0))
    # ID вашего телеграм-аккаунта для бота водителя
    DRIVER_CHAT_ID = "628521909"  # Получить через @userinfobot
    CLIENT_BOT_TOKEN = "7452398298:AAHoGk45AEJii2ycWaMCPKoHA5705ZyVEn0"
    DRIVER_BOT_TOKEN = "8012773257:AAHuhGx8TwaEP1KPooBFAq8EfUNSRZfmJtM"
    DRIVER_IDS = ['628521909', '987654321']  # Замените на реальные ID водителей