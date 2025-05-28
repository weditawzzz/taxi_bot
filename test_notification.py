import asyncio
import os
import sys

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
    else:
        print(f"❌ .env file not found at: {env_path}")
except ImportError:
    print("❌ python-dotenv not installed")

try:
    from core.bot_instance import Bots
    from core.config import Config

    print("✅ Импорты успешны")
except Exception as e:
    print(f"❌ Ошибка импорта: {e}")
    exit(1)


async def test_notification():
    try:
        # Получаем ID из конфигурации
        driver_chat_id = Config.DRIVER_CHAT_ID
        print(f"📞 Отправляем уведомление на ID: {driver_chat_id}")

        await Bots.driver.send_message(
            chat_id=driver_chat_id,
            text="🧪 <b>Тест уведомления водителя</b>\n\n"
                 "Если видите это сообщение - уведомления работают!\n\n"
                 "🚗 Система готова к приему заказов",
            parse_mode="HTML"
        )
        print("✅ Уведомление отправлено успешно!")

        # Тестируем уведомление о заказе
        await Bots.driver.send_message(
            chat_id=driver_chat_id,
            text="🚖 <b>ТЕСТОВЫЙ ЗАКАЗ</b>\n\n"
                 "📍 Откуда: ul. Żołnierska 1, Szczecin\n"
                 "📍 Куда: Ruska 21, Szczecin\n"
                 "💰 Цена: 25 PLN\n"
                 "👥 Пассажиров: 3\n"
                 "📏 Расстояние: ~5 км",
            parse_mode="HTML"
        )
        print("✅ Тестовый заказ отправлен!")

    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        print(f"🔍 Детали ошибки: {type(e).__name__}")


async def test_config():
    """Тестируем конфигурацию"""
    print("\n🔍 Проверяем конфигурацию:")
    print(f"DRIVER_CHAT_ID: {Config.DRIVER_CHAT_ID}")
    print(f"DRIVER_IDS: {Config.DRIVER_IDS}")
    print(f"CLIENT_BOT_TOKEN: {Config.CLIENT_BOT_TOKEN[:10]}...")
    print(f"DRIVER_BOT_TOKEN: {Config.DRIVER_BOT_TOKEN[:10]}...")


if __name__ == "__main__":
    try:
        asyncio.run(test_config())
        print("\n🚀 Отправляем тестовые уведомления...")
        asyncio.run(test_notification())
    except KeyboardInterrupt:
        print("\n👋 Тест прерван")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")