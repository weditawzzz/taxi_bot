# Также создайте файл: step_by_step_debug.py

"""
Пошаговая отладка проблемы с множественными водителями
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


async def debug_step_by_step():
    """Пошаговая отладка"""
    print("🔍 ПОШАГОВАЯ ОТЛАДКА ПРОБЛЕМЫ")
    print("=" * 50)

    # Шаг 1: Проверяем импорты
    print("1️⃣ Проверка импортов...")
    try:
        from core.services.driver_notification import driver_notification_service
        print("✅ driver_notification_service импортирован")

        from config import Config
        print("✅ Config импортирован")
        print(f"   DRIVER_IDS: {Config.DRIVER_IDS}")

        from core.handlers.driver.order_handlers import accept_order, reject_order
        print("✅ order_handlers импортированы")

    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return

    # Шаг 2: Проверяем методы сервиса
    print(f"\n2️⃣ Проверка методов сервиса...")
    print(f"   notify_all_drivers: {hasattr(driver_notification_service, 'notify_all_drivers')}")
    print(f"   handle_driver_response: {hasattr(driver_notification_service, 'handle_driver_response')}")
    print(f"   pending_orders: {type(driver_notification_service.pending_orders)}")
    print(f"   driver_responses: {type(driver_notification_service.driver_responses)}")

    # Шаг 3: Симулируем создание заказа
    print(f"\n3️⃣ Симуляция создания заказа...")
    order_id = 2001
    order_data = {
        'order_type': 'alcohol_delivery',
        'products': 'Тест продукты',
        'budget': 100,
        'address': 'Тест адрес',
        'client_id': 999888777
    }

    try:
        await driver_notification_service.notify_all_drivers(order_id, order_data)
        print(f"✅ notify_all_drivers вызван успешно")
        print(f"   Pending orders: {list(driver_notification_service.pending_orders.keys())}")

        if order_id not in driver_notification_service.pending_orders:
            print("❌ ПРОБЛЕМА: Заказ не сохранился в pending_orders!")
            return

    except Exception as e:
        print(f"❌ Ошибка при создании заказа: {e}")
        import traceback
        traceback.print_exc()
        return

    # Шаг 4: Симулируем отклонение первого водителя
    print(f"\n4️⃣ Симуляция отклонения первого водителя...")
    driver1_id = int(Config.DRIVER_IDS[0])

    try:
        print(f"   Водитель {driver1_id} отклоняет заказ {order_id}")
        result = await driver_notification_service.handle_driver_response(
            order_id, driver1_id, "reject"
        )

        print(f"   Результат: {result}")
        print(f"   Заказ в pending_orders: {order_id in driver_notification_service.pending_orders}")
        print(f"   Driver responses: {driver_notification_service.driver_responses.get(order_id, {})}")

        if order_id not in driver_notification_service.pending_orders:
            print("❌ НАЙДЕНА ПРОБЛЕМА: Заказ удаляется после одного отклонения!")
            print("❌ Проблема в функции handle_driver_response или _handle_driver_rejection")

            # Дополнительная диагностика
            print(f"\n🔍 ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА:")
            responses = driver_notification_service.driver_responses.get(order_id, {})
            all_drivers = [int(d) for d in Config.DRIVER_IDS]
            rejected_count = sum(1 for resp in responses.values() if resp == "reject")

            print(f"   Всего водителей: {len(all_drivers)}")
            print(f"   Отклонили: {rejected_count}")
            print(f"   Условие (rejected_count >= total): {rejected_count >= len(all_drivers)}")

            if rejected_count >= len(all_drivers):
                print("❌ ОШИБКА: Логика считает что все водители отклонили!")
                print("   Проверьте функцию _handle_driver_rejection")

            return
        else:
            print("✅ Заказ остался активным - правильно!")

    except Exception as e:
        print(f"❌ Ошибка при отклонении: {e}")
        import traceback
        traceback.print_exc()
        return

    # Шаг 5: Симулируем принятие вторым водителем
    if len(Config.DRIVER_IDS) > 1:
        print(f"\n5️⃣ Симуляция принятия вторым водителем...")
        driver2_id = int(Config.DRIVER_IDS[1])

        try:
            print(f"   Водитель {driver2_id} принимает заказ {order_id}")
            result = await driver_notification_service.handle_driver_response(
                order_id, driver2_id, "accept"
            )

            print(f"   Результат: {result}")
            print(f"   Заказ в pending_orders: {order_id in driver_notification_service.pending_orders}")

            if order_id in driver_notification_service.pending_orders:
                print("❌ ПРОБЛЕМА: Заказ не удаляется после принятия!")
            else:
                print("✅ Заказ удален после принятия - правильно!")

        except Exception as e:
            print(f"❌ Ошибка при принятии: {e}")
            import traceback
            traceback.print_exc()

    # Очистка
    driver_notification_service.pending_orders.clear()
    driver_notification_service.driver_responses.clear()

    print(f"\n🏁 Пошаговая отладка завершена!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(debug_step_by_step())