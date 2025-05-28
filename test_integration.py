# Создайте файл: test_integration.py

"""
Тест интеграции order_handlers с driver_notification_service
"""
import os
import sys
from pathlib import Path

# Загружаем .env
current_dir = Path(__file__).parent
env_file = current_dir / '.env'

if env_file.exists():
    from dotenv import load_dotenv

    load_dotenv(env_file)
    os.environ.setdefault('CLIENT_BOT_TOKEN', os.getenv('CLIENT_BOT_TOKEN', 'test'))
    os.environ.setdefault('DRIVER_BOT_TOKEN', os.getenv('DRIVER_BOT_TOKEN', 'test'))
else:
    os.environ['CLIENT_BOT_TOKEN'] = 'test_token'
    os.environ['DRIVER_BOT_TOKEN'] = 'test_token'

sys.path.insert(0, str(current_dir))


# Мокаем CallbackQuery для теста
class MockUser:
    def __init__(self, user_id, name):
        self.id = user_id
        self.full_name = name


class MockMessage:
    def __init__(self):
        self.message_id = 1

    async def edit_text(self, **kwargs):
        print(f"📝 [MOCK] Edit message: {kwargs.get('text', '')[:50]}...")

    async def answer(self, text, **kwargs):
        print(f"💬 [MOCK] Answer: {text[:50]}...")


class MockCallback:
    def __init__(self, user_id, name, order_id, action):
        self.from_user = MockUser(user_id, name)
        self.data = f"{action}_{order_id}"
        self.message = MockMessage()

    async def answer(self, text="", show_alert=False):
        if text:
            print(f"🔔 [MOCK] Callback answer: {text}")


async def test_integration():
    """Тест интеграции handlers с сервисом"""
    print("🔗 ТЕСТ ИНТЕГРАЦИИ order_handlers + driver_notification_service")
    print("=" * 70)

    try:
        # Импорты
        from core.services.driver_notification import driver_notification_service
        from config import Config

        print(f"✅ Импорты успешны")
        print(f"🚛 Водители: {Config.DRIVER_IDS}")

        # Создаем заказ в сервисе (как делает alcohol.py)
        order_id = 3001
        order_data = {
            'order_type': 'alcohol_delivery',
            'products': 'Тест продукты',
            'budget': 100,
            'address': 'Тест адрес',
            'client_id': 999888777,
            'user_id': 999888777
        }

        print(f"\n📦 Создаем заказ {order_id} в сервисе...")
        driver_notification_service.pending_orders[order_id] = order_data
        driver_notification_service.driver_responses[order_id] = {}

        print(f"📊 Pending orders: {list(driver_notification_service.pending_orders.keys())}")

        # Импортируем функции handlers
        from core.handlers.driver.order_handlers import reject_order, accept_order

        # Тест 1: Первый водитель отклоняет
        print(f"\n" + "=" * 50)
        print("ТЕСТ 1: Первый водитель отклоняет через handler")
        print("=" * 50)

        driver1_id = int(Config.DRIVER_IDS[0])
        mock_callback1 = MockCallback(driver1_id, "Водитель 1", order_id, "reject")

        print(f"❌ Водитель {driver1_id} нажимает 'Odrzuć' через handler...")
        await reject_order(mock_callback1)

        print(f"\n📊 Результат после отклонения через handler:")
        print(f"- Заказ в pending_orders: {order_id in driver_notification_service.pending_orders}")
        print(f"- Pending orders: {list(driver_notification_service.pending_orders.keys())}")
        print(f"- Driver responses: {driver_notification_service.driver_responses.get(order_id, {})}")

        if order_id in driver_notification_service.pending_orders:
            print("✅ ПРАВИЛЬНО: Заказ остался активным после отклонения через handler")

            # Тест 2: Второй водитель принимает
            if len(Config.DRIVER_IDS) > 1:
                print(f"\n" + "=" * 50)
                print("ТЕСТ 2: Второй водитель принимает через handler")
                print("=" * 50)

                driver2_id = int(Config.DRIVER_IDS[1])
                mock_callback2 = MockCallback(driver2_id, "Водитель 2", order_id, "accept")

                print(f"✅ Водитель {driver2_id} нажимает 'Przyjmij' через handler...")

                # Для теста accept нужно создать заказ в БД (мокаем)
                print("⚠️ Для полного теста accept нужна настоящая БД с заказом")
                print("⚠️ Пропускаем тест accept - он требует реальную БД")

        else:
            print("❌ ОШИБКА: Заказ исчез после отклонения через handler!")
            print("❌ Проблема в интеграции handler -> service")

        # Очистка
        driver_notification_service.pending_orders.clear()
        driver_notification_service.driver_responses.clear()

        print(f"\n🏁 Тест интеграции завершен!")

    except Exception as e:
        print(f"💥 Ошибка интеграционного теста: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_integration())