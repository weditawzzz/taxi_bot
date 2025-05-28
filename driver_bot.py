"""
Водительский бот для такси
"""
import asyncio
import logging
import sys
import os

# Добавляем текущую папку в путь Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Загружаем .env файл ДО импорта config
try:
    from dotenv import load_dotenv

    env_path = os.path.join(current_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Loaded .env file from: {env_path}")

        # Проверяем что токен загрузился
        driver_token = os.getenv('DRIVER_BOT_TOKEN')
        if driver_token:
            print(f"✅ DRIVER_BOT_TOKEN loaded: {driver_token[:10]}...")
        else:
            print("❌ DRIVER_BOT_TOKEN not found!")
    else:
        print(f"❌ .env file not found at: {env_path}")

except ImportError:
    print("❌ python-dotenv not installed. Installing...")
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv

    load_dotenv()

try:
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.fsm.storage.memory import MemoryStorage

    # Импортируем из исправленного core
    from core.config import config
    from core.database import init_database, close_database
    from core.handlers.driver import order_handlers, vehicle_handlers
    from core.handlers.driver import driver_start

    print("✅ All driver bot imports successful!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Current directory: {current_dir}")
    exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция водительского бота"""

    try:
        # Инициализация бота
        bot = Bot(
            token=config.driver_bot.token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

        # Создание диспетчера с хранилищем состояний
        dp = Dispatcher(storage=MemoryStorage())

        # Регистрация роутеров
        dp.include_router(driver_start.router)  # Водительский старт
        dp.include_router(order_handlers.router)  # Обработка заказов
        dp.include_router(vehicle_handlers.router)  # Управление авто

        # Создаем папки если их нет
        os.makedirs('data', exist_ok=True)
        os.makedirs('logs', exist_ok=True)

        # Инициализация базы данных
        logger.info("Initializing database...")
        await init_database()

        # Информация о боте
        bot_info = await bot.get_me()
        logger.info(f"Starting driver bot: @{bot_info.username}")

        # Уведомляем о запуске
        if config.debug:
            logger.info("🚗 Driver Bot started in DEBUG mode!")
        else:
            logger.info("🚗 Driver Bot started!")

        print(f"🎉 Driver Bot @{bot_info.username} is running!")
        print("💬 Go to Telegram and send /start to your driver bot!")
        print("🛑 Press Ctrl+C to stop")

        # Запуск long polling
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Error starting driver bot: {e}")
        if "Unauthorized" in str(e):
            print("❌ Driver bot token is invalid! Check your .env file.")
        raise

    finally:
        # Закрытие соединений
        logger.info("Shutting down driver bot...")
        try:
            await close_database()
            await bot.session.close()
        except:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Driver Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)