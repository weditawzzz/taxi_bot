from datetime import time


class Config:
    # Тарифы (всё в zł)
    DEFAULT_CITY = "Szczecin"
    GOOGLE_MAPS_API_KEY = "AIzaSyBHUFjfnp7oN4BC27_wlOuCqr33WOrNRQo"
    MAX_CITY_DISTANCE_KM = 25

    # Круглосуточные и поздние магазины алкоголя в Щецине
    ALCOHOL_SHOPS = {
        "zabka_plac_zolnierza": {
            "name": "Żabka Plac Żołnierza",
            "address": "Plac Żołnierza 1, Szczecin",
            "hours": "24/7",
            "phone": "+48 91 234 5678",
            "type": "convenience"
        },
        "fresh_market_ku_sloncu": {
            "name": "Fresh Market Ku Słońcu",
            "address": "Ku Słońcu 69, Szczecin",
            "hours": "06:00-23:00",
            "phone": "+48 91 123 4567",
            "type": "market"
        },
        "abc_wyszynskiego": {
            "name": "ABC Wyszyńskiego",
            "address": "Al. Piastów 42, Szczecin",
            "hours": "06:00-02:00",
            "phone": "+48 91 345 6789",
            "type": "convenience"
        },
        "shell_jasna": {
            "name": "Shell Jasna",
            "address": "Jasna 15, Szczecin",
            "hours": "24/7",
            "phone": "+48 91 456 7890",
            "type": "gas_station"
        },
        "zabka_centrum": {
            "name": "Żabka Centrum",
            "address": "Bolesława Krzywoustego 8, Szczecin",
            "hours": "24/7",
            "phone": "+48 91 567 8901",
            "type": "convenience"
        },
        "fresh_market_pilsudskiego": {
            "name": "Fresh Market Piłsudskiego",
            "address": "Marszałka Józefa Piłsudskiego 37, Szczecin",
            "hours": "06:00-23:00",
            "phone": "+48 91 678 9012",
            "type": "market"
        },
        "abc_wojska_polskiego": {
            "name": "ABC Wojska Polskiego",
            "address": "Al. Powstańców Wielkopolskich 69, Szczecin",
            "hours": "06:00-24:00",
            "phone": "+48 91 789 0123",
            "type": "convenience"
        },
        "shell_wojska_polskiego": {
            "name": "Shell Wojska Polskiego",
            "address": "Al. Wojska Polskiego 198, Szczecin",
            "hours": "24/7",
            "phone": "+48 91 890 1234",
            "type": "gas_station"
        },
        "zabka_komuny_paryskiej": {
            "name": "Żabka Komuny Paryskiej",
            "address": "Komuny Paryskiej 40, Szczecin",
            "hours": "24/7",
            "phone": "+48 91 901 2345",
            "type": "convenience"
        },
        "abc_bydgoska": {
            "name": "ABC Bydgoska",
            "address": "Bydgoska 1, Szczecin",
            "hours": "06:00-24:00",
            "phone": "+48 91 012 3456",
            "type": "convenience"
        }
    }

    TARIFFS = {
        "city": {"base": 10, "per_km": 3, "night_multiplier": 1.2},
        "airport": {
            "goleniow": 170,
            "berlin": 600,
            "night_multiplier": 1.2
        },
        "night_time": (time(22, 0), time(6, 0)),
        # Убираем старый тариф "alcohol" для собственного алкоголя
        "alcohol_delivery": {
            "base": 25,  # Базовая стоимость
            "per_km": 3,  # За километр
            "night_multiplier": 1.3,  # Ночной коэффициент +30%
            "service_fee": 15  # Плата за услугу покупки
        },
        "intercity": {"base": 10, "per_km": 2, "night_multiplier": 1.2, "min_distance": 50},
        "international": {"base": 10, "per_km": 2.5, "night_multiplier": 1.2}
    }

    # Время ночного тарифа
    NIGHT_HOURS = (time(22, 0), time(6, 0))
    # ID вашего телеграм-аккаунта для бота водителя
    DRIVER_CHAT_ID = "628521909"
    CLIENT_BOT_TOKEN = "7452398298:AAHoGk45AEJii2ycWaMCPKoHA5705ZyVEn0"
    DRIVER_BOT_TOKEN = "8012773257:AAHuhGx8TwaEP1KPooBFAq8EfUNSRZfmJtM"
    DRIVER_IDS = ['628521909', '987654321']