# Создайте файл: test_real_service.py

"""
Тест реального сервиса с правильной загрузкой конфигурации
"""
import os
import sys
from pathlib import Path

# Загружаем .env файл вручную
current_dir = Path(__file__).parent
env_file = current_dir / '.env'

if env_file.exists():
    print(f"📁 Loading .env from: {env_file}")
    from dotenv import load_dotenv

    load_dotenv(env_file)

    # Проверяем что токены загрузились
    client_token = os.getenv('CLIENT_BOT_TOKEN')
    driver_token = os.getenv('DRIVER_BOT_TOKEN')

    if client_token and driver_token:
        print(f"✅ Tokens loaded:")
        print(f"   CLIENT: {client_token[:10]}...")
        print(f"   DRIVER: {driver_token[:10]}...")
    else:
        print("❌ Tokens not found in .env")

    # Устанавливаем переменные окружения если их нет
    if not os.getenv('CLIENT_BOT_TOKEN'):
        print("⚙️ Setting CLIENT_BOT_TOKEN manually")
        os.environ['CLIENT_BOT_TOKEN'] = client_token or "test_token"
    if not os.getenv('DRIVER_BOT_TOKEN'):
        print("⚙️ Setting DRIVER_BOT_TOKEN manually")
        os.environ['DRIVER_BOT_TOKEN'] = driver_token or "test_token"
else:
    print(f"❌ .env file not found at: {env_file}")
    # Устанавливаем тестовые токены
    os.environ['CLIENT_BOT_TOKEN'] = "test_client_token"
    os.environ['DRIVER_BOT_TOKEN'] = "test_driver_token"
    print("⚙️ Using test tokens")

# Добавляем путь к проекту
sys.path.insert(0, str(current_dir))

import asyncio


async def test_real_service():
    """Тестирование реального сервиса"""
    print("\n🧪 Тестирование РЕАЛЬНОГО DriverNotificationService")
    print("=" * 60)

    try:
        # Импортируем реальный сервис
        from core.services.driver_notification import driver_notification_service
        from config import Config

        print(f"✅ Импорт успешный!")
        print(f"🚛 Available drivers: {Config.DRIVER_IDS}")
        print(f"📊 Current pending orders: {list(driver_notification_service.pending_orders.keys())}")

        # Тест логики как в простом тесте
        order_id = 1001
        order_data = {
            'order_type': 'alcohol_delivery',
            'products': 'Test products',
            'budget': 50,
            'address': 'Test address',
            'distance': 5.0,
            'price': 20,
            'client_id': 123456,
            'user_id': 123456
        }

        print(f"\n📦 Создаем тестовый заказ {order_id}")
        driver_notification_service.pending_orders[order_id] = order_data
        driver_notification_service.driver_responses[order_id] = {}

        print(f"📊 Pending orders: {list(driver_notification_service.pending_orders.keys())}")

        # Тест 1: Первый водитель отклоняет
        print(f"\n" + "=" * 40)
        print("ТЕСТ 1: Первый водитель отклоняет")
        print("=" * 40)

        driver1_id = int(Config.DRIVER_IDS[0])
        print(f"❌ Водитель {driver1_id} отклоняет заказ...")

        result = await driver_notification_service.handle_driver_response(
            order_id, driver1_id, "reject"
        )

        print(f"\n📊 Результат:")
        print(f"- Функция вернула: {result}")
        print(f"- Заказ в pending_orders: {order_id in driver_notification_service.pending_orders}")
        print(f"- Pending orders: {list(driver_notification_service.pending_orders.keys())}")
        print(f"- Driver responses: {driver_notification_service.driver_responses.get(order_id, {})}")

        if order_id in driver_notification_service.pending_orders:
            print("✅ ПРАВИЛЬНО: Заказ остался активным после одного отклонения")

            # Тест 2: Второй водитель принимает
            if len(Config.DRIVER_IDS) > 1:
                print(f"\n" + "=" * 40)
                print("ТЕСТ 2: Второй водитель принимает")
                print("=" * 40)

                driver2_id = int(Config.DRIVER_IDS[1])
                print(f"✅ Водитель {driver2_id} принимает заказ...")

                result2 = await driver_notification_service.handle_driver_response(
                    order_id, driver2_id, "accept"
                )

                print(f"\n📊 Результат:")
                print(f"- Функция вернула: {result2}")
                print(f"- Заказ в pending_orders: {order_id in driver_notification_service.pending_orders}")
                print(f"- Pending orders: {list(driver_notification_service.pending_orders.keys())}")

                if not (order_id in driver_notification_service.pending_orders):
                    print("✅ ПРАВИЛЬНО: Заказ удален после принятия")
                    print("✅ РЕАЛЬНЫЙ СЕРВИС РАБОТАЕТ КОРРЕКТНО!")
                else:
                    print("❌ ОШИБКА: Заказ не удален после принятия")
            else:
                print("⚠️ Только один водитель в конфиге")

        else:
            print("❌ КРИТИЧЕСКАЯ ОШИБКА: Заказ исчез после одного отклонения!")
            print("❌ РЕАЛЬНЫЙ СЕРВИС РАБОТАЕТ НЕПРАВИЛЬНО!")

        # Очищаем тестовые данные
        driver_notification_service.pending_orders.clear()
        driver_notification_service.driver_responses.clear()

        print(f"\n🏁 Тест реального сервиса завершен!")

    except Exception as e:
        print(f"💥 Ошибка при тестировании реального сервиса: {e}")
        import traceback
        traceback.print_exc()


async def test_real_config():
    """Проверка конфигурации"""
    print("\n🔧 Проверка конфигурации...")

    try:
        from config import Config
        print(f"✅ Config импортирован успешно")
        print(f"🚛 DRIVER_IDS: {Config.DRIVER_IDS}")
        print(f"📊 DRIVER_CHAT_ID: {getattr(Config, 'DRIVER_CHAT_ID', 'Not found')}")

        if hasattr(Config, 'DRIVER_IDS') and len(Config.DRIVER_IDS) >= 2:
            print("✅ Конфигурация водителей правильная")
        else:
            print("❌ Проблема с конфигурацией водителей")

    except Exception as e:
        print(f"❌ Ошибка импорта конфигурации: {e}")


async def main():
    """Главная функция"""
    await test_real_config()
    await test_real_service()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Тест прерван")
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()