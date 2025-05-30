# ОКОНЧАТЕЛЬНО ИСПРАВЛЕНО: order_handlers.py - точные фильтры callback

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton
from core.models import Session, Ride as Order, Vehicle as DriverVehicle
from core.bot_instance import Bots
from config import Config
from core.handlers.driver.vehicle_handlers import get_vehicle_keyboard
import logging

logger = logging.getLogger(__name__)
router = Router()


async def get_user_language_simple(user_id: int) -> str:
    """Простая функция получения языка пользователя"""
    try:
        from core.services.user_service import UserService
        user_service = UserService()
        user = await user_service.get_user_by_telegram_id(user_id)
        return user.language if user and user.language else "pl"
    except Exception:
        return "pl"


def is_numeric_order_id(callback_data: str) -> bool:
    """Проверяет, является ли callback данными с числовым ID заказа"""
    try:
        parts = callback_data.split("_")
        if len(parts) >= 2:
            int(parts[1])  # Пытаемся преобразовать в число
            return True
        return False
    except (ValueError, IndexError):
        return False


@router.callback_query(F.data.startswith("accept_") & F.func(lambda call: is_numeric_order_id(call.data)))
async def accept_order(callback: CallbackQuery):
    """Handle order acceptance by driver - ТОЛЬКО для числовых ID заказов"""
    try:
        print(f"🎬 [HANDLER] Accept order callback from driver {callback.from_user.id}")
        print(f"📝 [HANDLER] Callback data: {callback.data}")

        # Проверяем, является ли пользователь водителем
        if str(callback.from_user.id) not in Config.DRIVER_IDS:
            await callback.answer("Эта функция доступна только водителям", show_alert=True)
            return

        # Безопасно извлекаем order_id
        try:
            order_id = int(callback.data.split("_")[1])
        except (ValueError, IndexError) as e:
            print(f"❌ [HANDLER] Invalid callback format: {callback.data}, error: {e}")
            await callback.answer("❌ Неверный формат данных")
            return

        print(f"📦 [HANDLER] Processing accept for order {order_id}")

        # Используем новый сервис множественных водителей если доступен
        try:
            from core.services.driver_notification import driver_notification_service

            # Проверяем через сервис
            if order_id not in driver_notification_service.pending_orders:
                print(f"❌ [HANDLER] Order {order_id} not in pending orders")
                await callback.answer("❌ Заказ уже принят другим водителем или отменен", show_alert=True)
                await callback.message.edit_text("ℹ️ <b>Заказ больше недоступен</b>", parse_mode="HTML")
                return
        except ImportError:
            print("⚠️ [HANDLER] Driver notification service not available, using basic acceptance")

        with Session() as session:
            # Получаем заказ из базы данных
            order = session.query(Order).get(order_id)
            if not order:
                print(f"❌ [HANDLER] Order {order_id} not found in database")
                await callback.answer("Zamówienie nie zostało znalezione!")
                return

            # Проверяем статус заказа в базе данных
            if order.status != "pending":
                print(f"❌ [HANDLER] Order {order_id} status is {order.status}, not pending")
                await callback.answer("❌ Заказ уже принят другим водителем", show_alert=True)
                await callback.message.edit_text("ℹ️ <b>Заказ уже принят</b>", parse_mode="HTML")
                return

            # Проверяем данные автомобиля водителя
            vehicle = session.query(DriverVehicle).filter_by(driver_id=callback.from_user.id).first()
            if not vehicle:
                print(f"⚠️ [HANDLER] No vehicle data for driver {callback.from_user.id}")
                await callback.answer()
                lang = await get_user_language_simple(callback.from_user.id)
                await callback.message.answer(
                    "⚠️ Перед принятием заказа необходимо добавить данные об автомобиле",
                    reply_markup=get_vehicle_keyboard(lang)
                )
                return

            print(f"🚗 [HANDLER] Vehicle found for driver: {vehicle.model}")

            # Обновляем статус заказа в базе данных
            order.status = "accepted"
            order.driver_id = callback.from_user.id
            order.driver_name = callback.from_user.full_name

            # Формируем информацию об автомобиле
            car_info = f"{vehicle.color} {vehicle.model} ({vehicle.license_plate})"

            session.commit()
            print(f"💾 [HANDLER] Order {order_id} updated in database")

            # Обрабатываем через сервис ПОСЛЕ обновления БД если доступен
            try:
                from core.services.driver_notification import driver_notification_service
                print(f"📢 [HANDLER] Notifying service about acceptance...")
                await driver_notification_service.handle_driver_response(
                    order_id, callback.from_user.id, "accept"
                )
            except ImportError:
                print("⚠️ [HANDLER] Driver notification service not available")

            # Отправляем клиенту уведомление с кнопками управления поездкой
            client_id = getattr(order, 'client_id', getattr(order, 'user_id', None))
            if client_id:
                # Импортируем новые клавиатуры
                try:
                    from core.keyboards import get_client_ride_keyboard
                    lang = await get_user_language_simple(client_id)
                    client_keyboard = get_client_ride_keyboard(lang, "accepted")
                except ImportError:
                    client_keyboard = None

                # Формируем сообщение для клиента с правильной ценой алкоголя
                if order.order_type == "alcohol_delivery" or (order.notes and "ALCOHOL DELIVERY" in order.notes):
                    arrival_time = "~30-45 minut"
                    budget_info = f" (do {getattr(order, 'budget', 'N/A')} zł)" if hasattr(order,
                                                                                           'budget') and order.budget else ""

                    # ФИКСИРОВАННАЯ ЦЕНА 20 zł для алкоголя
                    alcohol_delivery_price = 20

                    message_text = (
                        "✅ <b>Kierowca zaakceptował zamówienie zakupu!</b>\n\n"
                        f"👤 <b>Kierowca:</b> {callback.from_user.full_name}\n"
                        f"🚗 <b>Samochód:</b> {car_info}\n"
                        f"🕒 <b>Szacowany czas:</b> {arrival_time}\n\n"
                        "🛒 <b>Proces realizacji:</b>\n"
                        "1. Kierowca kupi produkty w sklepie\n"
                        "2. Dostarczy je pod wskazany adres\n"
                        "3. Przedstawi paragon do zapłaty\n\n"
                        f"💵 <b>Do zapłaty:</b>\n"
                        f"- Opłata za usługę: {alcohol_delivery_price} zł\n"
                        f"- Koszt zakupów{budget_info}\n\n"
                        "⚠️ <b>Przygotuj:</b>\n"
                        "1. Dowód osobisty\n"
                        "2. Gotówkę na pełną kwotę"
                    )
                else:
                    arrival_time = "~10 minut"
                    message_text = (
                        "✅ <b>Kierowca zaakceptował Twoje zamówienie!</b>\n\n"
                        f"👤 <b>Kierowca:</b> {callback.from_user.full_name}\n"
                        f"🚗 <b>Samochód:</b> {car_info}\n"
                        f"🕒 <b>Czas dojazdu:</b> {arrival_time}\n\n"
                        f"💵 <b>Do zapłaty:</b> {getattr(order, 'estimated_price', getattr(order, 'price', 0))} zł\n\n"
                        "🎯 Водитель едет к вам. Вы можете отслеживать его местоположение."
                    )

                # Отправляем уведомление клиенту
                try:
                    await Bots.client.send_message(
                        chat_id=client_id,
                        text=message_text,
                        reply_markup=client_keyboard,
                        parse_mode="HTML",
                        disable_notification=False
                    )
                    print(f"📱 [HANDLER] Client {client_id} notified about acceptance")
                except Exception as e:
                    print(f"❌ [HANDLER] Error notifying client: {e}")

            # Отправляем водителю расширенную клавиатуру управления поездкой
            try:
                lang = await get_user_language_simple(callback.from_user.id)

                # Импортируем новые клавиатуры
                from core.keyboards import get_driver_ride_keyboard
                ride_keyboard = get_driver_ride_keyboard(lang, "accepted")

                await Bots.driver.send_message(
                    chat_id=callback.from_user.id,
                    text=(
                        f"🎯 <b>УПРАВЛЕНИЕ ЗАКАЗОМ #{order_id}</b>\n\n"
                        f"📍 Едьте к пассажиру: {order.pickup_address}\n"
                        f"⏰ Ожидаемое время прибытия: ~10 минут\n\n"
                        f"Используйте кнопки ниже для управления заказом:"
                    ),
                    reply_markup=ride_keyboard,
                    parse_mode="HTML"
                )

                print(f"✅ [HANDLER] Sent ride management interface to driver {callback.from_user.id}")

            except Exception as e:
                logger.error(f"Error sending ride management interface: {e}")

            # Подтверждаем водителю
            await callback.answer("✅ Zamówienie zaakceptowane!")

            # Обновляем сообщение водителя с правильной ценой
            if order.order_type == "alcohol_delivery" or (order.notes and "ALCOHOL DELIVERY" in order.notes):
                products = getattr(order, 'products', 'Zobacz szczegóły w zamówieniu')
                if order.notes and "Products:" in order.notes:
                    try:
                        products = order.notes.split("Products:")[1].split(",")[0].strip()
                    except:
                        pass

                confirmation_text = "✅ <b>ZAMÓWIENIE PRZYJĘTE</b>\n\n"
                confirmation_text += (
                    f"🛒 <b>Twoje zadania:</b>\n"
                    f"1. Wybierz najbliższy sklep\n"
                    f"2. Kup: {products}\n"
                    f"3. Zachowaj paragon!\n"
                    f"4. Dostarcz na: {order.destination_address}\n\n"
                    f"💰 <b>Budżet klienta:</b> {getattr(order, 'budget', 'N/A')} zł\n"
                    f"💵 <b>Twoja opłata:</b> 20 zł\n\n"  # ФИКСИРОВАННАЯ ЦЕНА
                    f"👤 <b>Клиент:</b> {client_id}\n"
                    f"🚗 <b>Ваше авто:</b> {car_info}"
                )
            else:
                confirmation_text = (
                    f"✅ <b>ЗАКАЗ ПРИНЯТ</b>\n\n"
                    f"📍 <b>Откуда:</b> {order.pickup_address}\n"
                    f"📍 <b>Куда:</b> {order.destination_address}\n"
                    f"👥 <b>Пассажиров:</b> {getattr(order, 'passengers_count', 1)}\n"
                    f"💵 <b>Стоимость:</b> {getattr(order, 'estimated_price', getattr(order, 'price', 0))} zł\n\n"
                    f"👤 <b>Клиент:</b> {client_id}\n"
                    f"🚗 <b>Ваше авто:</b> {car_info}"
                )

            await callback.message.edit_text(
                text=confirmation_text,
                parse_mode="HTML"
            )

            print(f"✅ [HANDLER] Order {order_id} processed successfully")

    except Exception as e:
        print(f"💥 [HANDLER] Error in accept_order: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("Wystąpił błąd podczas przetwarzania zamówienia")


@router.callback_query(F.data.startswith("reject_") & F.func(lambda call: is_numeric_order_id(call.data)))
async def reject_order(callback: CallbackQuery):
    """Handle order rejection by driver - ТОЛЬКО для числовых ID заказов"""
    try:
        print(f"🎬 [HANDLER] Reject order callback from driver {callback.from_user.id}")
        print(f"📝 [HANDLER] Callback data: {callback.data}")

        # Безопасно извлекаем order_id
        try:
            order_id = int(callback.data.split("_")[1])
        except (ValueError, IndexError) as e:
            print(f"❌ [HANDLER] Invalid callback format: {callback.data}, error: {e}")
            await callback.answer("❌ Неверный формат данных")
            return

        print(f"📦 [HANDLER] Processing reject for order {order_id}")

        # Используем новый сервис множественных водителей если доступен
        try:
            from core.services.driver_notification import driver_notification_service

            # Проверяем через сервис
            if order_id not in driver_notification_service.pending_orders:
                print(f"❌ [HANDLER] Order {order_id} not in pending orders")
                await callback.answer("ℹ️ Заказ уже обработан", show_alert=True)
                await callback.message.edit_text("ℹ️ <b>Заказ больше недоступен</b>", parse_mode="HTML")
                return

            # Обрабатываем отклонение только через сервис
            print(f"📢 [HANDLER] Notifying service about rejection...")
            await driver_notification_service.handle_driver_response(
                order_id, callback.from_user.id, "reject"
            )
        except ImportError:
            print("⚠️ [HANDLER] Driver notification service not available, using basic rejection")
            # Базовая обработка отклонения без сервиса

        await callback.answer("❌ Zamówienie odrzucone")
        await callback.message.edit_text(
            text=f"❌ <b>ЗАКАЗ ОТКЛОНЕН</b>\n\nВы отклонили заказ #{order_id}\n\n⏳ Другие водители все еще могут его принять.",
            parse_mode="HTML"
        )

        print(f"✅ [HANDLER] Rejection for order {order_id} processed successfully")

    except Exception as e:
        print(f"💥 [HANDLER] Error in reject_order: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("Wystąpił błąd podczas przetwarzania zamówienia")


@router.message(F.location)
async def handle_driver_location_enhanced(message: Message):
    """Улучшенная обработка локации водителя с множественными статусами"""
    try:
        with Session() as session:
            # Обновляем локацию водителя в базе
            driver = session.query(DriverVehicle).filter_by(driver_id=message.from_user.id).first()
            if driver and hasattr(driver, 'last_lat'):
                driver.last_lat = message.location.latitude
                driver.last_lon = message.location.longitude
                session.commit()

            # Находим активный заказ водителя (расширенный поиск по статусам)
            order = session.query(Order).filter_by(
                driver_id=message.from_user.id
            ).filter(Order.status.in_(["accepted", "driver_arrived", "in_progress"])).order_by(
                Order.created_at.desc()).first()

            if not order:
                await message.answer("ℹ️ Нет активных заказов для отслеживания геопозиции")
                return

            # Отправляем локацию пассажиру
            client_id = getattr(order, 'client_id', getattr(order, 'user_id', None))
            if client_id:
                try:
                    await Bots.client.send_location(
                        chat_id=client_id,
                        latitude=message.location.latitude,
                        longitude=message.location.longitude,
                        disable_notification=True
                    )

                    # Отправляем статус в зависимости от стадии поездки
                    if order.status == "accepted":
                        status_text = "🚗 Kierowca jedzie do Ciebie"
                    elif order.status == "driver_arrived":
                        status_text = "✅ Kierowca czeka na miejscu"
                    elif order.status == "in_progress":
                        status_text = "🚦 Podróż w toku"
                    else:
                        status_text = "📍 Aktualizacja lokalizacji"

                    await Bots.client.send_message(
                        chat_id=client_id,
                        text=f"📍 {status_text}",
                        disable_notification=True
                    )

                    print(f"📍 [LOCATION] Sent location update to client {client_id} for order {order.id}")

                except Exception as e:
                    print(f"❌ [LOCATION] Error sending location to client: {e}")

            await message.answer("✅ Местоположение обновлено", disable_notification=True)

    except Exception as e:
        print(f"💥 [LOCATION] Error in location handler: {e}")
        await message.answer("❌ Błąd podczas aktualizacji lokalizacji")


# ===================================================================
# КОМАНДЫ ДЛЯ ТЕСТИРОВАНИЯ И ОТЛАДКИ
# ===================================================================

@router.message(F.text.startswith("/test_callback_routing"))
async def test_callback_routing(message: Message):
    """ТЕСТ: Проверка маршрутизации callback"""
    if str(message.from_user.id) not in Config.DRIVER_IDS:
        return

    try:
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        # Создаем тестовые кнопки разных типов
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ TEST: accept_123", callback_data="accept_123")
        builder.button(text="❌ TEST: reject_456", callback_data="reject_456")
        builder.button(text="⏸️ TEST: accept_waiting", callback_data="accept_waiting")
        builder.button(text="🚗 TEST: driver_arrived", callback_data="driver_arrived")
        builder.adjust(2)

        await message.answer(
            "🧪 <b>TEST МАРШРУТИЗАЦИИ CALLBACK</b>\n\n"
            "📊 Проверка:\n"
            "• accept_123, reject_456 → order_handlers\n"
            "• accept_waiting, driver_arrived → ride_handlers\n\n"
            "Нажмите кнопки для проверки:",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка создания тестовых кнопок: {e}")


@router.message(F.text.startswith("/check_alcohol_price"))
async def check_alcohol_price(message: Message):
    """Команда для проверки правильности цен на алкоголь"""
    if str(message.from_user.id) not in Config.DRIVER_IDS:
        return

    try:
        # Проверяем текущие заказы алкоголя в базе
        with Session() as session:
            alcohol_orders = session.query(Order).filter_by(order_type="alcohol_delivery").limit(5).all()

            if not alcohol_orders:
                await message.answer("📊 Заказов алкоголя не найдено")
                return

            result_text = "📊 <b>ПРОВЕРКА ЦЕН НА АЛКОГОЛЬ</b>\n\n"

            for order in alcohol_orders:
                price = getattr(order, 'estimated_price', getattr(order, 'price', 0))
                status = "✅" if float(price) == 20.0 else "❌"

                result_text += (
                    f"{status} <b>Заказ #{order.id}</b>\n"
                    f"   Цена: {price} zł\n"
                    f"   Статус: {order.status}\n"
                    f"   Продукты: {getattr(order, 'products', 'N/A')[:50]}...\n\n"
                )

            result_text += (
                f"\n💡 <b>Правильная цена алкоголя: 20 zł</b>\n"
                f"❌ Если видите другие цены - значит есть ошибка"
            )

            await message.answer(result_text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Ошибка проверки: {e}")


# ===================================================================
# ОТЛАДОЧНЫЕ ЛОГИ ДЛЯ МОНИТОРИНГА CALLBACK
# ===================================================================

@router.callback_query(F.data.in_(["debug_order_test"]))
async def debug_order_handlers(callback: CallbackQuery):
    """Отладочный обработчик для тестирования order_handlers"""
    print(f"🔧 [ORDER_DEBUG] Debug callback in order_handlers: {callback.data}")
    await callback.answer("🔧 ORDER_DEBUG: Этот callback обработан в order_handlers")


# НЕ ДОБАВЛЯЕМ УНИВЕРСАЛЬНЫЙ ПЕРЕХВАТЧИК - пусть другие callback проходят дальше
print("📋 [ORDER_HANDLERS] Loaded with selective callback filtering")