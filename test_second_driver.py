import asyncio
import os
import sys

# Добавляем текущую папку в путь Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Загружаем .env файл
try:
    from dotenv import load_dotenv

    env_path = os.path.join(current_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Loaded .env file from: {env_path}")
except ImportError:
    print("❌ python-dotenv not installed")

try:
    from core.bot_instance import Bots
    from core.config import Config

    print("✅ Импорты успешны")
except Exception as e:
    print(f"❌ Ошибка импорта: {e}")
    exit(1)


async def test_both_drivers():
    """Тестируем уведомления обоим водителям"""
    try:
        print(f"🔍 DRIVER_IDS из конфигурации: {Config.DRIVER_IDS}")
        print(f"📞 DRIVER_CHAT_ID: {Config.DRIVER_CHAT_ID}")

        # Тестируем каждого водителя отдельно
        for i, driver_id in enumerate(Config.DRIVER_IDS, 1):
            try:
                print(f"\n📱 Отправляем тест водителю #{i} (ID: {driver_id})")

                await Bots.driver.send_message(
                    chat_id=driver_id,
                    text=f"🧪 <b>Тест #{i}</b>\n\n"
                         f"Водитель ID: {driver_id}\n"
                         f"Если видите это - уведомления работают!",
                    parse_mode="HTML"
                )
                print(f"✅ Водитель {driver_id} - сообщение отправлено")

            except Exception as e:
                print(f"❌ Ошибка для водителя {driver_id}: {e}")

        # Тестируем групповую отправку
        print(f"\n🚀 Тестируем групповую отправку...")

        from core.services.driver_notification import driver_notification_service

        success = await driver_notification_service.notify_all_drivers(99999, {
            'pickup_address': 'Тестовый адрес подачи',
            'destination_address': 'Тестовый адрес назначения',
            'distance_km': 5.0,
            'estimated_price': 25.0,
            'passengers_count': 2,
            'order_type': 'city_ride'
        })

        if success:
            print("✅ Групповая отправка успешна")
        else:
            print("❌ Ошибка групповой отправки")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(test_both_drivers())
    except KeyboardInterrupt:
        print("\n👋 Тест прерван")
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")