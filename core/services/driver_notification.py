# Замените содержимое core/services/driver_notification.py на это:

"""
Сервис для уведомления множественных водителей - С ОБЩИМ ХРАНИЛИЩЕМ
УЛУЧШЕНО: Автоудаление спама и чистые уведомления
"""
import asyncio
import logging
import sqlite3
import json
from typing import Dict, List, Set
from pathlib import Path
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from decimal import Decimal

# Импортируем конфигурацию безопасно
try:
    from core.bot_instance import Bots
    from config import Config
except ImportError:
    # Fallback для тестирования
    class MockBots:
        class driver:
            @staticmethod
            async def send_message(*args, **kwargs):
                print(f"📨 [MOCK] Отправка сообщения: {args}")

            @staticmethod
            async def delete_message(*args, **kwargs):
                print(f"🗑️ [MOCK] Удаление сообщения: {args}")

        class client:
            @staticmethod
            async def send_message(*args, **kwargs):
                print(f"📨 [MOCK] Отправка сообщения клиенту: {args}")


    class MockConfig:
        DRIVER_IDS = ['628521909', '6158974369']


    Bots = MockBots()
    Config = MockConfig()

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Кастомный энкодер для сериализации Decimal объектов"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class SharedOrderStorage:
    """Общее хранилище заказов между ботами через SQLite"""

    def __init__(self):
        self.db_path = Path("data/shared_orders.db")
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Инициализация БД"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                         CREATE TABLE IF NOT EXISTS pending_orders
                         (
                             order_id
                             INTEGER
                             PRIMARY
                             KEY,
                             order_data
                             TEXT
                             NOT
                             NULL,
                             created_at
                             TIMESTAMP
                             DEFAULT
                             CURRENT_TIMESTAMP
                         )
                         """)

            conn.execute("""
                         CREATE TABLE IF NOT EXISTS driver_responses
                         (
                             order_id
                             INTEGER,
                             driver_id
                             INTEGER,
                             response
                             TEXT,
                             created_at
                             TIMESTAMP
                             DEFAULT
                             CURRENT_TIMESTAMP,
                             PRIMARY
                             KEY
                         (
                             order_id,
                             driver_id
                         )
                             )
                         """)

            # НОВАЯ ТАБЛИЦА: Хранение ID сообщений для автоудаления
            conn.execute("""
                         CREATE TABLE IF NOT EXISTS driver_messages
                         (
                             driver_id
                             INTEGER,
                             message_id
                             INTEGER,
                             order_id
                             INTEGER,
                             created_at
                             TIMESTAMP
                             DEFAULT
                             CURRENT_TIMESTAMP,
                             PRIMARY
                             KEY
                         (
                             driver_id,
                             message_id
                         )
                             )
                         """)

    def add_order(self, order_id: int, order_data: dict):
        """Добавить заказ"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO pending_orders (order_id, order_data) VALUES (?, ?)",
                (order_id, json.dumps(order_data, cls=DecimalEncoder, ensure_ascii=False))
            )
            print(f"💾 [STORAGE] Order {order_id} added to shared storage")

    def get_order(self, order_id: int) -> dict:
        """Получить заказ"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT order_data FROM pending_orders WHERE order_id = ?",
                (order_id,)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return {}

    def remove_order(self, order_id: int):
        """Удалить заказ"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM pending_orders WHERE order_id = ?", (order_id,))
            conn.execute("DELETE FROM driver_responses WHERE order_id = ?", (order_id,))
            conn.execute("DELETE FROM driver_messages WHERE order_id = ?", (order_id,))
            print(f"🗑️ [STORAGE] Order {order_id} removed from shared storage")

    def get_all_orders(self) -> List[int]:
        """Получить все активные заказы"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT order_id FROM pending_orders")
            return [row[0] for row in cursor.fetchall()]

    def add_response(self, order_id: int, driver_id: int, response: str):
        """Добавить ответ водителя"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO driver_responses (order_id, driver_id, response) VALUES (?, ?, ?)",
                (order_id, driver_id, response)
            )
            print(f"📝 [STORAGE] Response from driver {driver_id} for order {order_id}: {response}")

    def get_responses(self, order_id: int) -> Dict[int, str]:
        """Получить все ответы для заказа"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT driver_id, response FROM driver_responses WHERE order_id = ?",
                (order_id,)
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

    # НОВЫЕ МЕТОДЫ для управления сообщениями
    def add_message(self, driver_id: int, message_id: int, order_id: int):
        """Сохранить ID сообщения для автоудаления"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO driver_messages (driver_id, message_id, order_id) VALUES (?, ?, ?)",
                (driver_id, message_id, order_id)
            )

    def get_driver_messages(self, driver_id: int, order_id: int = None) -> List[int]:
        """Получить ID сообщений водителя"""
        with sqlite3.connect(self.db_path) as conn:
            if order_id:
                cursor = conn.execute(
                    "SELECT message_id FROM driver_messages WHERE driver_id = ? AND order_id = ?",
                    (driver_id, order_id)
                )
            else:
                cursor = conn.execute(
                    "SELECT message_id FROM driver_messages WHERE driver_id = ?",
                    (driver_id,)
                )
            return [row[0] for row in cursor.fetchall()]

    def remove_driver_messages(self, driver_id: int, order_id: int = None):
        """Удалить записи о сообщениях"""
        with sqlite3.connect(self.db_path) as conn:
            if order_id:
                conn.execute(
                    "DELETE FROM driver_messages WHERE driver_id = ? AND order_id = ?",
                    (driver_id, order_id)
                )
            else:
                conn.execute("DELETE FROM driver_messages WHERE driver_id = ?", (driver_id,))


class DriverNotificationService:
    """Сервис для управления уведомлениями водителей с общим хранилищем"""

    def __init__(self):
        self.storage = SharedOrderStorage()
        self.notification_tasks: Dict[int, asyncio.Task] = {}  # Только таймеры локально

    @property
    def pending_orders(self) -> Dict[int, Dict]:
        """Эмуляция старого интерфейса для совместимости"""
        orders = {}
        for order_id in self.storage.get_all_orders():
            orders[order_id] = self.storage.get_order(order_id)
        return orders

    @property
    def driver_responses(self) -> Dict[int, Dict[int, str]]:
        """Эмуляция старого интерфейса для ответов водителей"""
        responses = {}
        for order_id in self.storage.get_all_orders():
            responses[order_id] = self.storage.get_responses(order_id)
        return responses

    async def notify_all_drivers(self, order_id: int, order_data: dict):
        """Отправить уведомление всем водителям"""
        try:
            print(f"🚀 [SERVICE] Starting notification for order {order_id}")

            # Сохраняем заказ в общее хранилище
            self.storage.add_order(order_id, order_data)

            # Проверяем что заказ сохранился
            all_orders = self.storage.get_all_orders()
            print(f"📊 [SERVICE] All orders in shared storage: {all_orders}")

            # Отправляем уведомления всем водителям
            drivers = getattr(Config, 'DRIVER_IDS', ['628521909', '6158974369'])
            success_count = 0

            for driver_id in drivers:
                try:
                    await self._send_clean_notification(int(driver_id), order_id, order_data)
                    success_count += 1
                    print(f"✅ [SERVICE] Notified driver {driver_id}")
                    await asyncio.sleep(0.2)
                except Exception as e:
                    print(f"❌ [SERVICE] Failed to notify driver {driver_id}: {e}")

            if success_count > 0:
                # Запускаем таймер автоотмены
                self.notification_tasks[order_id] = asyncio.create_task(
                    self._auto_cancel_order(order_id)
                )
                print(f"⏰ [SERVICE] Started timer for order {order_id}")
                print(f"🎯 [SERVICE] Successfully notified {success_count}/{len(drivers)} drivers")
            else:
                await self._notify_client_no_drivers(order_data)
                self.storage.remove_order(order_id)
                print(f"⚠️ [SERVICE] No drivers notified, order cleaned up")

        except Exception as e:
            print(f"💥 [SERVICE] Critical error in notify_all_drivers: {e}")
            import traceback
            traceback.print_exc()

    async def _send_clean_notification(self, driver_id: int, order_id: int, order_data: dict):
        """НОВЫЙ МЕТОД: Отправить чистое уведомление без спама"""
        try:
            # Очищаем старые сообщения перед отправкой нового
            await self._cleanup_old_messages(driver_id)

            # Создаем кнопки
            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Przyjmij", callback_data=f"accept_{order_id}")
            builder.button(text="❌ Odrzuć", callback_data=f"reject_{order_id}")

            # Формируем качественное сообщение
            if order_data.get('order_type') == 'alcohol_delivery':
                text = (
                    f"🛒 <b>DOSTAWA ALKOHOLU #{order_id}</b>\n\n"
                    f"📝 <b>Produkty:</b> {order_data.get('products', 'N/A')}\n"
                    f"💰 <b>Budżet:</b> {order_data.get('budget', 'N/A')} zł\n"
                    f"📍 <b>Adres:</b> {order_data.get('address', 'N/A')}\n"
                    f"📏 <b>Dystans:</b> ~{order_data.get('distance', 5):.1f} km\n"
                    f"💵 <b>Zarobek:</b> {order_data.get('price', 20)} zł\n\n"
                    f"⏰ <b>Czas na odpowiedź:</b> 2 minuty"
                )
            else:
                text = (
                    f"🚖 <b>NOWE ZAMÓWIENIE #{order_id}</b>\n\n"
                    f"📍 <b>Z:</b> {order_data.get('pickup_address', 'N/A')}\n"
                    f"📍 <b>Do:</b> {order_data.get('destination_address', 'N/A')}\n"
                    f"📏 <b>Dystans:</b> {order_data.get('distance_km', 0):.1f} km\n"
                    f"💵 <b>Cena:</b> {order_data.get('estimated_price', 0)} zł\n"
                    f"👥 <b>Pasażerów:</b> {order_data.get('passengers_count', 1)}\n\n"
                    f"⏰ <b>Czas na odpowiedź:</b> 2 minuty"
                )

            # Отправляем ОДНО сообщение с уведомлением
            message = await Bots.driver.send_message(
                chat_id=driver_id,
                text=text,
                reply_markup=builder.as_markup(),
                parse_mode="HTML",
                disable_notification=False  # Звук только для новых заказов
            )

            # Сохраняем ID сообщения для автоудаления
            self.storage.add_message(driver_id, message.message_id, order_id)
            print(f"📱 [CLEAN] Sent clean notification to driver {driver_id}")

        except Exception as e:
            print(f"❌ [CLEAN] Error sending clean notification to driver {driver_id}: {e}")
            raise

    async def _cleanup_old_messages(self, driver_id: int):
        """Удаляет старые сообщения водителю"""
        try:
            message_ids = self.storage.get_driver_messages(driver_id)

            # Удаляем старые сообщения (оставляем только последние 2)
            if len(message_ids) > 2:
                to_delete = message_ids[:-2]  # Все кроме последних 2

                for message_id in to_delete:
                    try:
                        await Bots.driver.delete_message(chat_id=driver_id, message_id=message_id)
                        print(f"🗑️ [CLEAN] Deleted old message {message_id} for driver {driver_id}")
                    except TelegramBadRequest:
                        pass  # Сообщение уже удалено или недоступно
                    except Exception as e:
                        print(f"⚠️ [CLEAN] Could not delete message {message_id}: {e}")

                # Очищаем записи об удаленных сообщениях
                self.storage.remove_driver_messages(driver_id)

                # Оставляем записи о последних 2 сообщениях
                for message_id in message_ids[-2:]:
                    self.storage.add_message(driver_id, message_id, 0)  # order_id = 0 для старых

        except Exception as e:
            print(f"❌ [CLEAN] Error cleaning up messages for driver {driver_id}: {e}")

    async def _send_driver_notification(self, driver_id: int, order_id: int, order_data: dict):
        """СТАРЫЙ МЕТОД: Оставлен для совместимости"""
        await self._send_clean_notification(driver_id, order_id, order_data)

    async def handle_driver_response(self, order_id: int, driver_id: int, response: str):
        """Обработать ответ водителя - С ОБЩИМ ХРАНИЛИЩЕМ"""
        try:
            print(f"🎬 [SERVICE] Processing {response} from driver {driver_id} for order {order_id}")

            # Проверяем заказ в общем хранилище
            all_orders = self.storage.get_all_orders()
            print(f"📊 [SERVICE] Orders in shared storage: {all_orders}")

            if order_id not in all_orders:
                print(f"⚠️ [SERVICE] Order {order_id} NOT in shared storage")
                return False

            order_data = self.storage.get_order(order_id)
            if not order_data:
                print(f"❌ [SERVICE] No order data for {order_id}")
                return False

            # Записываем ответ в общее хранилище
            self.storage.add_response(order_id, driver_id, response)

            # Получаем все ответы
            responses = self.storage.get_responses(order_id)
            print(f"📝 [SERVICE] All responses for order {order_id}: {responses}")

            if response == "accept":
                print(f"✅ [SERVICE] ORDER ACCEPTED: {order_id} by driver {driver_id}")
                await self._handle_order_accepted(order_id, driver_id, order_data)
                return True

            elif response == "reject":
                print(f"❌ [SERVICE] ORDER REJECTED: {order_id} by driver {driver_id}")
                await self._handle_driver_rejection(order_id, driver_id, responses)
                return True

        except Exception as e:
            print(f"💥 [SERVICE] Error in handle_driver_response: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _handle_order_accepted(self, order_id: int, accepting_driver_id: int, order_data: dict):
        """Обработать принятие заказа"""
        try:
            print(f"🎉 [SERVICE] Processing ORDER ACCEPTANCE: {order_id} by driver {accepting_driver_id}")

            # Отменяем таймер
            if order_id in self.notification_tasks:
                self.notification_tasks[order_id].cancel()
                del self.notification_tasks[order_id]
                print(f"⏰ [SERVICE] Cancelled auto-cancel timer for order {order_id}")

            # НОВОЕ: Отправляем чистые уведомления другим водителям
            drivers = getattr(Config, 'DRIVER_IDS', ['628521909', '6158974369'])
            for driver_str in drivers:
                driver_id = int(driver_str)
                if driver_id != accepting_driver_id:
                    try:
                        # Отправляем уведомление о том, что заказ принят
                        message = await Bots.driver.send_message(
                            chat_id=driver_id,
                            text=f"✅ <b>Заказ #{order_id} принят другим водителем</b>",
                            parse_mode="HTML",
                            disable_notification=True  # Без звука
                        )

                        # Автоудаление через 3 секунды
                        asyncio.create_task(self._delete_message_after_delay(driver_id, message.message_id, 3))

                        print(f"📢 [SERVICE] Notified driver {driver_id} that order {order_id} was taken")
                    except Exception as e:
                        print(f"❌ [SERVICE] Failed to notify driver {driver_id}: {e}")

            # Удаляем из общего хранилища
            self.storage.remove_order(order_id)
            print(f"✅ [SERVICE] Order {order_id} processed and cleaned up successfully")

        except Exception as e:
            print(f"💥 [SERVICE] Error handling order acceptance: {e}")

    async def _handle_driver_rejection(self, order_id: int, rejecting_driver_id: int, responses: Dict[int, str]):
        """Обработать отклонение"""
        try:
            print(f"👎 [SERVICE] Processing REJECTION from driver {rejecting_driver_id} for order {order_id}")

            drivers = getattr(Config, 'DRIVER_IDS', ['628521909', '6158974369'])
            all_drivers = [int(d) for d in drivers]

            rejected_drivers = [d_id for d_id, resp in responses.items() if resp == "reject"]
            rejected_count = len(rejected_drivers)
            total_drivers = len(all_drivers)

            print(f"📊 [SERVICE] REJECTION STATUS for order {order_id}:")
            print(f"   - Rejected by {rejected_count}/{total_drivers} drivers")
            print(f"   - Rejected drivers: {rejected_drivers}")
            print(f"   - All responses: {responses}")

            if rejected_count >= total_drivers:
                print(f"🚫 [SERVICE] ALL {total_drivers} DRIVERS REJECTED ORDER {order_id}")
                order_data = self.storage.get_order(order_id)
                await self._cancel_order_all_rejected(order_id, order_data)
            else:
                remaining = total_drivers - rejected_count
                print(f"⏳ [SERVICE] Order {order_id} REMAINS ACTIVE - {remaining} drivers can still accept")

        except Exception as e:
            print(f"💥 [SERVICE] Error handling driver rejection: {e}")

    async def _cancel_order_all_rejected(self, order_id: int, order_data: dict):
        """Отменить заказ когда ВСЕ водители отклонили"""
        try:
            print(f"🚫 [SERVICE] CANCELLING ORDER {order_id} - all drivers rejected")

            # Отменяем таймер если есть
            if order_id in self.notification_tasks:
                self.notification_tasks[order_id].cancel()
                del self.notification_tasks[order_id]

            # Уведомляем клиента
            client_id = order_data.get('client_id') or order_data.get('user_id')
            if client_id:
                await Bots.client.send_message(
                    chat_id=client_id,
                    text=(
                        "😞 <b>Przepraszamy</b>\n\n"
                        "Niestety wszyscy dostępni kierowcy są obecnie zajęci.\n"
                        "Spróbuj ponownie za kilka minut."
                    ),
                    parse_mode="HTML",
                    disable_notification=False
                )
                print(f"📱 [SERVICE] Notified client {client_id} about order {order_id} rejection")

            self.storage.remove_order(order_id)
            print(f"✅ [SERVICE] Order {order_id} cancelled and cleaned up successfully")

        except Exception as e:
            print(f"💥 [SERVICE] Error cancelling order: {e}")

    async def _auto_cancel_order(self, order_id: int):
        """Автоматическая отмена по таймауту"""
        try:
            print(f"⏰ [SERVICE] Starting 120 second timer for order {order_id}")
            await asyncio.sleep(120)

            # Проверяем что заказ еще существует
            all_orders = self.storage.get_all_orders()
            if order_id in all_orders:
                print(f"⏰ [SERVICE] AUTO-CANCELLING order {order_id} due to timeout")

                order_data = self.storage.get_order(order_id)
                client_id = order_data.get('client_id') or order_data.get('user_id')

                if client_id:
                    await Bots.client.send_message(
                        chat_id=client_id,
                        text=(
                            "⏰ <b>Upłynął czas oczekiwania</b>\n\n"
                            "Niestety kierowcy nie odpowiedzieli na Twoje zamówienie.\n"
                            "Spróbuj ponownie."
                        ),
                        parse_mode="HTML",
                        disable_notification=False
                    )

                # НОВОЕ: Отправляем чистые уведомления о тайм-ауте
                drivers = getattr(Config, 'DRIVER_IDS', ['628521909', '6158974369'])
                for driver_str in drivers:
                    try:
                        message = await Bots.driver.send_message(
                            chat_id=int(driver_str),
                            text=f"⏰ <b>Заказ #{order_id} отменен по тайм-ауту</b>",
                            parse_mode="HTML",
                            disable_notification=True  # Без звука
                        )

                        # Автоудаление через 5 секунд
                        asyncio.create_task(self._delete_message_after_delay(int(driver_str), message.message_id, 5))

                    except Exception as e:
                        print(f"❌ [SERVICE] Failed to notify driver {driver_str} about timeout: {e}")

                self.storage.remove_order(order_id)
                print(f"⏰ [SERVICE] Order {order_id} auto-cancelled successfully")
            else:
                print(f"⏰ [SERVICE] Order {order_id} already processed before timeout")

        except asyncio.CancelledError:
            print(f"⏰ [SERVICE] Timer for order {order_id} was cancelled (order was accepted)")
        except Exception as e:
            print(f"💥 [SERVICE] Error in auto-cancel: {e}")

    async def _delete_message_after_delay(self, chat_id: int, message_id: int, delay_seconds: int):
        """НОВЫЙ МЕТОД: Удаляет сообщение через заданное время"""
        try:
            await asyncio.sleep(delay_seconds)
            await Bots.driver.delete_message(chat_id=chat_id, message_id=message_id)
            print(f"🗑️ [CLEAN] Auto-deleted message {message_id} after {delay_seconds}s")
        except TelegramBadRequest:
            pass  # Сообщение уже удалено
        except Exception as e:
            print(f"⚠️ [CLEAN] Could not delete message {message_id}: {e}")

    async def _notify_client_no_drivers(self, order_data: dict):
        """Уведомить клиента об отсутствии водителей"""
        try:
            client_id = order_data.get('client_id') or order_data.get('user_id')
            if client_id:
                await Bots.client.send_message(
                    chat_id=client_id,
                    text=(
                        "😞 <b>Brak dostępnych kierowców</b>\n\n"
                        "Przepraszamy, obecnie żaden kierowca nie jest dostępny.\n"
                        "Spróbuj ponownie za kilka minut."
                    ),
                    parse_mode="HTML",
                    disable_notification=False
                )
                print(f"📱 [SERVICE] Notified client {client_id} about no available drivers")
        except Exception as e:
            print(f"💥 [SERVICE] Error notifying client: {e}")


# Глобальный экземпляр сервиса
driver_notification_service = DriverNotificationService()