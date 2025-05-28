# ИСПРАВЛЕНО: order_handlers.py с фиксированной ценой алкоголя 20 zł

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton
from core.models import Session, Ride as Order, Vehicle as DriverVehicle
from core.bot_instance import Bots
from config import Config
from core.handlers.driver.vehicle_handlers import get_vehicle_keyboard

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


@router.callback_query(F.data.startswith("accept_"))
async def accept_order(callback: CallbackQuery):
    """ИСПРАВЛЕНО: Handle order acceptance by driver с правильной ценой алкоголя"""
    try:
        print(f"🎬 [HANDLER] Accept order callback from driver {callback.from_user.id}")

        # Проверяем, является ли пользователь водителем
        if str(callback.from_user.id) not in Config.DRIVER_IDS:
            await callback.answer("Эта функция доступна только водителям", show_alert=True)
            return

        order_id = int(callback.data.split("_")[1])
        print(f"📦 [HANDLER] Processing accept for order {order_id}")

        # Используем новый сервис множественных водителей
        from core.services.driver_notification import driver_notification_service

        # КРИТИЧЕСКИ ВАЖНО: Проверяем через сервис
        if order_id not in driver_notification_service.pending_orders:
            print(
                f"❌ [HANDLER] Order {order_id} not in pending orders: {list(driver_notification_service.pending_orders.keys())}")
            await callback.answer("❌ Заказ уже принят другим водителем или отменен", show_alert=True)
            await callback.message.edit_text("ℹ️ <b>Заказ больше недоступен</b>", parse_mode="HTML")
            return

        print(f"✅ [HANDLER] Order {order_id} found in pending orders")

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

            # КРИТИЧЕСКИ ВАЖНО: Обрабатываем через сервис ПОСЛЕ обновления БД
            print(f"📢 [HANDLER] Notifying service about acceptance...")
            await driver_notification_service.handle_driver_response(
                order_id, callback.from_user.id, "accept"
            )

            # ИСПРАВЛЕНО: Формируем сообщение для клиента с правильной ценой алкоголя
            if order.order_type == "alcohol_delivery" or (order.notes and "ALCOHOL DELIVERY" in order.notes):
                arrival_time = "~30-45 minut"
                budget_info = f" (do {getattr(order, 'budget', 'N/A')} zł)" if hasattr(order,
                                                                                       'budget') and order.budget else ""

                # ИСПРАВЛЕНО: Фиксированная цена 20 zł для алкоголя
                alcohol_delivery_price = 20  # ФИКСИРОВАННАЯ ЦЕНА

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
                    f"- Opłata za usługę: {alcohol_delivery_price} zł\n"  # ИСПРАВЛЕНО: 20 zł
                    f"- Koszt zakupów{budget_info}\n\n"
                    "⚠️ <b>Przygotuj:</b>\n"
                    "1. Dowód osobisty\n"
                    "2. Gotówkę na pełną kwotę"
                )
            else:
                arrival_time = "~10 minut"
                message_text = (
                    "✅ <b>Kierowca zaakceptował Twoje zamówienie!</b>\n\n"
                    f"👤 Kierowca: {callback.from_user.full_name}\n"
                    f"🚗 Samochód: {car_info}\n"
                    f"🕒 Czas dojazdu: {arrival_time}\n\n"
                    f"💵 Do zapłaty: {getattr(order, 'estimated_price', getattr(order, 'price', 0))} zł"
                )

            # Отправляем уведомление клиенту
            try:
                client_id = getattr(order, 'client_id', getattr(order, 'user_id', None))
                if client_id:
                    await Bots.client.send_message(
                        chat_id=client_id,
                        text=message_text,
                        parse_mode="HTML",
                        disable_notification=False
                    )
                    print(f"📱 [HANDLER] Client {client_id} notified about acceptance")
            except Exception as e:
                print(f"❌ [HANDLER] Error notifying client: {e}")

            # Отправляем кнопку для геолокации водителю
            location_keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📍 Транслировать геопозицию", request_location=True)]
                ],
                resize_keyboard=True
            )
            await Bots.driver.send_message(
                chat_id=callback.from_user.id,
                text="Нажмите кнопку, чтобы пассажир видел ваше местоположение",
                reply_markup=location_keyboard
            )

            # Подтверждаем водителю
            await callback.answer("✅ Zamówienie zaakceptowane!")

            # ИСПРАВЛЕНО: Обновляем сообщение водителя с правильной ценой
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
                    f"💵 <b>Twoja opłata:</b> 20 zł\n\n"  # ИСПРАВЛЕНО: Фиксированная цена
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


@router.callback_query(F.data.startswith("reject_"))
async def reject_order(callback: CallbackQuery):
    """Handle order rejection by driver - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        print(f"🎬 [HANDLER] Reject order callback from driver {callback.from_user.id}")

        order_id = int(callback.data.split("_")[1])
        print(f"📦 [HANDLER] Processing reject for order {order_id}")

        # Используем новый сервис множественных водителей
        from core.services.driver_notification import driver_notification_service

        # КРИТИЧЕСКИ ВАЖНО: Проверяем через сервис
        if order_id not in driver_notification_service.pending_orders:
            print(
                f"❌ [HANDLER] Order {order_id} not in pending orders: {list(driver_notification_service.pending_orders.keys())}")
            await callback.answer("ℹ️ Заказ уже обработан", show_alert=True)
            await callback.message.edit_text("ℹ️ <b>Заказ больше недоступен</b>", parse_mode="HTML")
            return

        print(f"✅ [HANDLER] Order {order_id} found in pending orders")

        # ВАЖНО: НЕ обновляем статус в базе данных при отклонении одним водителем
        # ВАЖНО: НЕ уведомляем клиента здесь - это сделает сервис если нужно

        # Обрабатываем отклонение только через сервис
        print(f"📢 [HANDLER] Notifying service about rejection...")
        await driver_notification_service.handle_driver_response(
            order_id, callback.from_user.id, "reject"
        )

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
        await callback.answer("Wystąpił błąд podczas przetwarzania zamówienia")


@router.message(F.location)
async def handle_driver_location(message: Message):
    """Handle driver's location updates"""
    with Session() as session:
        # Обновляем локацию водителя
        driver = session.query(DriverVehicle).filter_by(driver_id=message.from_user.id).first()
        if driver:
            if hasattr(driver, 'last_lat'):
                driver.last_lat = message.location.latitude
                driver.last_lon = message.location.longitude
                session.commit()

        # Отправляем локацию пассажиру, если есть активный заказ
        order = session.query(Order).filter_by(
            driver_id=message.from_user.id,
            status="accepted"
        ).order_by(Order.created_at.desc()).first()

        if order:
            try:
                client_id = getattr(order, 'client_id', getattr(order, 'user_id', None))
                if client_id:
                    await Bots.client.send_location(
                        chat_id=client_id,
                        latitude=message.location.latitude,
                        longitude=message.location.longitude,
                        disable_notification=False
                    )
                    await message.answer("✅ Пассажир получил ваше местоположение")
            except Exception as e:
                print(f"❌ Error sending location to client: {e}")


# ДОПОЛНИТЕЛЬНАЯ КОМАНДА ДЛЯ ПРОВЕРКИ ЦЕН АЛКОГОЛЯ
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


# КОМАНДА ДЛЯ ПРОВЕРКИ ТИПОВ АВТОМОБИЛЕЙ
@router.message(F.text.startswith("/check_vehicle_types"))
async def check_vehicle_types(message: Message):
    """Команда для проверки типов автомобилей"""

    if str(message.from_user.id) not in Config.DRIVER_IDS:
        return

    try:
        with Session() as session:
            vehicles = session.query(DriverVehicle).all()

            if not vehicles:
                await message.answer("🚗 Автомобилей не найдено")
                return

            result_text = "🚗 <b>ПРОВЕРКА ТИПОВ АВТОМОБИЛЕЙ</b>\n\n"

            lancer_sportback_count = 0

            for vehicle in vehicles:
                vehicle_type = getattr(vehicle, 'vehicle_type', 'N/A')

                # Проверяем Lancer Sportback
                if (vehicle.model and 'lancer' in vehicle.model.lower() and
                        'sportback' in vehicle.model.lower()):
                    lancer_sportback_count += 1
                    status = "✅" if vehicle_type == "HATCHBACK" else "❌"
                    result_text += f"{status} <b>Lancer Sportback</b> → {vehicle_type}\n"

            result_text += f"\n📊 <b>Статистика:</b>\n"
            result_text += f"Всего автомобилей: {len(vehicles)}\n"
            result_text += f"Lancer Sportback: {lancer_sportback_count}\n"

            if lancer_sportback_count > 0:
                result_text += f"\n💡 <b>Lancer Sportback должен быть HATCHBACK</b>"

            await message.answer(result_text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Ошибка проверки: {e}")