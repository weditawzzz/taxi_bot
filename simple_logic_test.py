# Создайте файл: simple_logic_test.py

"""
Простой тест логики без зависимостей от конфигурации
"""


class MockConfig:
    DRIVER_IDS = ['628521909', '6158974369']


# Мокаем все зависимости
class MockBots:
    class driver:
        @staticmethod
        async def send_message(*args, **kwargs):
            print(f"📨 [MOCK] Отправка сообщения водителю: {args[0] if args else 'Unknown'}")


class DriverNotificationService:
    """Упрощенная версия сервиса для тестирования логики"""

    def __init__(self):
        self.pending_orders = {}
        self.driver_responses = {}
        self.notification_tasks = {}

    async def handle_driver_response(self, order_id: int, driver_id: int, response: str):
        """Основная логика обработки ответов"""
        print(f"🎬 Processing {response} from driver {driver_id} for order {order_id}")

        # Проверяем заказ
        if order_id not in self.pending_orders:
            print(f"❌ Order {order_id} NOT in pending orders: {list(self.pending_orders.keys())}")
            return False

        # Инициализируем ответы
        if order_id not in self.driver_responses:
            self.driver_responses[order_id] = {}

        # Записываем ответ
        self.driver_responses[order_id][driver_id] = response
        print(f"📝 Updated responses for {order_id}: {self.driver_responses[order_id]}")

        if response == "accept":
            print(f"✅ ACCEPT: Order {order_id} by driver {driver_id}")
            await self._handle_order_accepted(order_id, driver_id)
            return True

        elif response == "reject":
            print(f"❌ REJECT: Order {order_id} by driver {driver_id}")
            await self._handle_driver_rejection(order_id, driver_id)
            return True

        return False

    async def _handle_order_accepted(self, order_id: int, accepting_driver_id: int):
        """Обработка принятия заказа"""
        print(f"🎉 Handling acceptance of order {order_id} by driver {accepting_driver_id}")

        # Уведомляем других водителей
        for driver_str in MockConfig.DRIVER_IDS:
            driver_id = int(driver_str)
            if driver_id != accepting_driver_id:
                await MockBots.driver.send_message(driver_id, f"Order {order_id} taken")

        # Очищаем заказ
        self._cleanup_order(order_id)
        print(f"✅ Order {order_id} processed successfully")

    async def _handle_driver_rejection(self, order_id: int, rejecting_driver_id: int):
        """Обработка отклонения - КЛЮЧЕВАЯ ЛОГИКА"""
        print(f"👎 Handling rejection from driver {rejecting_driver_id}")

        responses = self.driver_responses.get(order_id, {})
        all_drivers = [int(d) for d in MockConfig.DRIVER_IDS]

        rejected_drivers = [d_id for d_id, resp in responses.items() if resp == "reject"]
        rejected_count = len(rejected_drivers)
        total_drivers = len(all_drivers)

        print(f"📊 Rejection status: {rejected_count}/{total_drivers}")
        print(f"📋 Rejected by: {rejected_drivers}")
        print(f"📋 All responses: {responses}")

        # КРИТИЧЕСКАЯ ПРОВЕРКА
        if rejected_count >= total_drivers:
            print(f"🚫 ALL {total_drivers} drivers rejected order {order_id}")
            await self._cancel_order_all_rejected(order_id)
        else:
            remaining = total_drivers - rejected_count
            print(f"⏳ Order {order_id} still has {remaining} drivers who can accept")
            print(f"🔄 Order {order_id} remains ACTIVE")

    async def _cancel_order_all_rejected(self, order_id: int):
        """Отмена заказа когда все отклонили"""
        print(f"🚫 Cancelling order {order_id} - all drivers rejected")
        await MockBots.driver.send_message("client", "All drivers rejected")
        self._cleanup_order(order_id)

    def _cleanup_order(self, order_id: int):
        """Очистка заказа"""
        print(f"🧹 Cleaning up order {order_id}")
        self.pending_orders.pop(order_id, None)
        self.driver_responses.pop(order_id, None)
        print(f"📊 Remaining orders: {list(self.pending_orders.keys())}")


async def test_logic():
    """Тестирование логики"""
    print("🧪 Тестирование логики DriverNotificationService")
    print("=" * 60)

    service = DriverNotificationService()

    # Создаем тестовый заказ
    order_id = 999
    order_data = {'type': 'alcohol', 'client_id': 123}

    print(f"📦 Создаем заказ {order_id}")
    service.pending_orders[order_id] = order_data
    service.driver_responses[order_id] = {}

    print(f"📊 Pending orders: {list(service.pending_orders.keys())}")
    print(f"🚛 Available drivers: {MockConfig.DRIVER_IDS}")

    # Тест 1: Первый водитель отклоняет
    print(f"\n" + "=" * 40)
    print("ТЕСТ 1: Первый водитель отклоняет")
    print("=" * 40)

    driver1_id = int(MockConfig.DRIVER_IDS[0])
    print(f"❌ Водитель {driver1_id} отклоняет заказ...")

    result = await service.handle_driver_response(order_id, driver1_id, "reject")

    print(f"\n📊 Результат:")
    print(f"- Функция вернула: {result}")
    print(f"- Заказ в pending_orders: {order_id in service.pending_orders}")
    print(f"- Pending orders: {list(service.pending_orders.keys())}")

    if order_id in service.pending_orders:
        print("✅ ПРАВИЛЬНО: Заказ остался активным после одного отклонения")

        # Тест 2: Второй водитель принимает
        print(f"\n" + "=" * 40)
        print("ТЕСТ 2: Второй водитель принимает")
        print("=" * 40)

        driver2_id = int(MockConfig.DRIVER_IDS[1])
        print(f"✅ Водитель {driver2_id} принимает заказ...")

        result2 = await service.handle_driver_response(order_id, driver2_id, "accept")

        print(f"\n📊 Результат:")
        print(f"- Функция вернула: {result2}")
        print(f"- Заказ в pending_orders: {order_id in service.pending_orders}")
        print(f"- Pending orders: {list(service.pending_orders.keys())}")

        if not (order_id in service.pending_orders):
            print("✅ ПРАВИЛЬНО: Заказ удален после принятия")
        else:
            print("❌ ОШИБКА: Заказ не удален после принятия")

    else:
        print("❌ ОШИБКА: Заказ исчез после одного отклонения!")
        return

    # Тест 3: Все водители отклоняют
    print(f"\n" + "=" * 40)
    print("ТЕСТ 3: Все водители отклоняют")
    print("=" * 40)

    order_id2 = 998
    service.pending_orders[order_id2] = order_data
    service.driver_responses[order_id2] = {}

    print(f"📦 Создаем заказ {order_id2}")

    for i, driver_str in enumerate(MockConfig.DRIVER_IDS):
        driver_id = int(driver_str)
        print(f"❌ Водитель {driver_id} ({i + 1}/{len(MockConfig.DRIVER_IDS)}) отклоняет...")

        await service.handle_driver_response(order_id2, driver_id, "reject")

        print(f"   Заказ в pending_orders: {order_id2 in service.pending_orders}")

    print(f"\n📊 Финальный результат:")
    print(f"- Заказ в pending_orders: {order_id2 in service.pending_orders}")

    if not (order_id2 in service.pending_orders):
        print("✅ ПРАВИЛЬНО: Заказ удален после отклонения всеми")
    else:
        print("❌ ОШИБКА: Заказ остался после отклонения всеми")

    print(f"\n🏁 Тестирование завершено!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_logic())