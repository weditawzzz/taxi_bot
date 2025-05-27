"""
Запуск клиентского бота для заказа такси
"""
import asyncio
import logging
import sys
import os

# Добавляем текущую папку в путь Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# ВАЖНО: Загружаем .env файл ДО импорта config
try:
    from dotenv import load_dotenv

    # Загружаем .env файл
    env_path = os.path.join(current_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Loaded .env file from: {env_path}")

        # Проверяем что токен загрузился
        client_token = os.getenv('CLIENT_BOT_TOKEN')
        if client_token:
            print(f"✅ CLIENT_BOT_TOKEN loaded: {client_token[:10]}...")
        else:
            print("❌ CLIENT_BOT_TOKEN not found!")
    else:
        print(f"❌ .env file not found at: {env_path}")

except ImportError:
    print("❌ python-dotenv not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv
    load_dotenv()

# Проверяем что все папки на месте
required_paths = [
    os.path.join(current_dir, 'core'),
    os.path.join(current_dir, 'core', 'config.py'),
    os.path.join(current_dir, 'core', 'database.py'),
]

for path in required_paths:
    if not os.path.exists(path):
        print(f"❌ Missing: {path}")
        exit(1)

try:
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    # Импортируем напрямую из core
    from core.config import config
    from core.database import init_database, close_database
    from core.handlers.client.start import client_router
    from core.handlers.client.city_ride import city_ride_router

    # Импортируем новый обработчик алкоголя
    try:
        from core.handlers.client.alcohol import router as alcohol_router
        alcohol_available = True
    except ImportError as e:
        print(f"⚠️ Alcohol handler not available: {e}")
        alcohol_router = None
        alcohol_available = False

    print("✅ All imports successful!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Current directory: {current_dir}")
    print("Files in current directory:")
    for item in os.listdir(current_dir):
        print(f"  - {item}")

    # Более детальная диагностика для обработчика алкоголя
    alcohol_path = os.path.join(current_dir, 'core', 'handlers', 'client', 'alcohol.py')
    if os.path.exists(alcohol_path):
        print(f"✅ Alcohol handler exists at: {alcohol_path}")
    else:
        print(f"❌ Alcohol handler missing: {alcohol_path}")

    exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция клиентского бота"""

    try:
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

        # Добавляем обработчик алкоголя если доступен
        if alcohol_available and alcohol_router:
            dp.include_router(alcohol_router)
            logger.info("🍷 Alcohol delivery module loaded!")
        else:
            logger.warning("⚠️ Alcohol delivery module not loaded")

        # Создаем папки если их нет
        os.makedirs('data', exist_ok=True)
        os.makedirs('logs', exist_ok=True)

        # Инициализация базы данных
        logger.info("Initializing database...")
        await init_database()

        # Информация о боте
        bot_info = await bot.get_me()
        logger.info(f"Starting client bot: @{bot_info.username}")

        # Уведомляем о запуске
        if config.debug:
            logger.info("🚖 Client Taxi Bot started in DEBUG mode!")
            if alcohol_available:
                logger.info("🍷 Alcohol delivery module loaded!")
        else:
            logger.info("🚖 Client Taxi Bot started!")
            if alcohol_available:
                logger.info("🍷 Alcohol delivery module loaded!")

        print(f"🎉 Bot @{bot_info.username} is running!")
        print("💬 Go to Telegram and send /start to your bot!")
        if alcohol_available:
            print("🍷 Alcohol delivery from shops is now available!")
        print("🛑 Press Ctrl+C to stop")

        # Запуск long polling
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        if "Unauthorized" in str(e):
            print("❌ Bot token is invalid! Check your .env file.")
        elif "alcohol" in str(e).lower():
            print("❌ Error loading alcohol module. Check alcohol.py file.")
        raise

    finally:
        # Закрытие соединений
        logger.info("Shutting down...")
        try:
            await close_database()
            await bot.session.close()
        except:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)