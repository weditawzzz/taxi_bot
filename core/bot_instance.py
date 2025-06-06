from aiogram import Bot
from core.config import Config  # Исправленный импорт

class Bots:
    client = Bot(token=Config.CLIENT_BOT_TOKEN)
    driver = Bot(token=Config.DRIVER_BOT_TOKEN)

# Для обратной совместимости
bots = {
    "client": Bots.client,
    "driver": Bots.driver
}
bot = Bots.client
driver_bot = Bots.driver