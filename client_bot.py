"""
Клиентский бот для заказа такси
"""
import asyncio
import logging
import sys
import os

# Добавляем текущую папку в путь Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from taxi_bot.core.config import config
from taxi_bot.core.database import init_database, close_database
from taxi_bot.core.handlers.client.start import client_router
from taxi_bot.core.handlers.client.city_ride import city_ride_router
from core.handlers.client.taxi_ride import taxi_router


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция клиентского бота"""

    # Инициализация бота
    bot = Bot(
        token=config.client_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Создание диспетчера
    dp = Dispatcher()

    # Регистрация роутеров
    dp.include_router(client_router)
    dp.include_router(city_ride_router)
    dp.include_router(taxi_router)

    try:
        # Инициализация базы данных
        logger.info("Initializing database...")
        await init_database()

        # Информация о боте
        bot_info = await bot.get_me()
        logger.info(f"Starting client bot: @{bot_info.username}")

        # Уведомляем о запуске
        if config.debug:
            logger.info("🚖 Client Taxi Bot started in DEBUG mode!")
        else:
            logger.info("🚖 Client Taxi Bot started!")

        # Запуск long polling
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

    finally:
        # Закрытие соединений
        logger.info("Shutting down...")
        await close_database()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)