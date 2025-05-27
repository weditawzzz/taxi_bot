from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton
from core.models import Session, Order, DriverVehicle
from core.bot_instance import Bots
from config import Config
from core.handlers.driver.vehicle_handlers import get_vehicle_keyboard
from core.services.user_service import get_user_language

router = Router()


@router.callback_query(F.data.startswith("accept_"))
async def accept_order(callback: CallbackQuery):
    """Handle order acceptance by driver"""
    try:
        # Проверяем, является ли пользователь водителем
        if str(callback.from_user.id) not in Config.DRIVER_IDS:
            await callback.answer("Эта функция доступна только водителям", show_alert=True)
            return

        order_id = int(callback.data.split("_")[1])

        with Session() as session:
            # Сначала получаем заказ
            order = session.query(Order).get(order_id)
            if not order:
                await callback.answer("Zamówienie nie zostało znalezione!")
                return

            # Затем проверяем авто водителя
            vehicle = session.query(DriverVehicle).filter_by(driver_id=callback.from_user.id).first()
            if not vehicle:
                await callback.answer()
                lang = get_user_language(callback.from_user.id)
                await callback.message.answer(
                    "⚠️ Перед принятием заказа необходимо добавить данные об автомобиле",
                    reply_markup=get_vehicle_keyboard(lang)
                )
                return

            # Обновляем статус заказа
            order.status = "accepted"
            order.driver_id = callback.from_user.id
            order.driver_name = callback.from_user.full_name

            # Формируем информацию об автомобиле
            car_info = f"{vehicle.color} {vehicle.model} ({vehicle.license_plate})"

            session.commit()

            # Формируем сообщение для клиента в зависимости от типа заказа
            if order.order_type == "alcohol_delivery":
                # Новый тип: покупка и доставка из магазина
                arrival_time = "~30-45 minut"
                budget_info = f" (do {order.budget} zł)" if hasattr(order, 'budget') and order.budget else ""
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
                    f"- Opłata za usługę: {order.price} zł\n"
                    f"- Koszt zakupów{budget_info}\n\n"
                    "⚠️ <b>Przygotuj:</b>\n"
                    "1. Dowód osobisty\n"
                    "2. Gotówkę na pełną kwotę"
                )
            elif order.order_type == "alcohol":
                # Старый тип: доставка собственного алкоголя (на случай если остались)
                arrival_time = "~15 minut"
                message_text = (
                    "✅ <b>Kierowca zaakceptował Twoje zamówienie!</b>\n\n"
                    f"👤 Kierowca: {callback.from_user.full_name}\n"
                    f"🚗 Samochód: {car_info}\n"
                    f"🕒 Czas dojazdu: {arrival_time}\n\n"
                    "🍾 <b>Dostawa alkoholu:</b>\n"
                    "- 20 zł za dostawę (gotówka)\n"
                    "- + kwota z paragonu\n\n"
                    "⚠️ Przygotuj:\n"
                    "1. Dowód osobisty\n"
                    "2. Gotówkę"
                )
            else:
                # Обычные поездки
                arrival_time = "~10 minut"
                message_text = (
                    "✅ <b>Kierowca zaakceptował Twoje zamówienie!</b>\n\n"
                    f"👤 Kierowca: {callback.from_user.full_name}\n"
                    f"🚗 Samochód: {car_info}\n"
                    f"🕒 Czas dojazdu: {arrival_time}\n\n"
                    f"💵 Do zapłaty: {order.price} zł ({order.payment_method})"
                )

            # Отправляем уведомление клиенту
            try:
                await Bots.client.send_message(
                    chat_id=order.user_id,
                    text=message_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Błąd wysyłania wiadomości do klienta: {e}")

            # Отправляем кнопку для трансляции геопозиции водителю
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
            await callback.answer("Zamówienie zaakceptowane!")

            # Обновляем сообщение водителя
            if order.order_type == "alcohol_delivery":
                confirmation_text = "✅ <b>ZAMÓWIENIE PRZYJĘTE</b>\n\n"
                confirmation_text += (
                    f"🛒 <b>Twoje zadania:</b>\n"
                    f"1. Wybierz najbliższy sklep\n"
                    f"2. Kup: {order.products}\n"
                    f"3. Zachowaj paragon!\n"
                    f"4. Dostarcz na: {order.destination}\n\n"
                    f"💰 <b>Budżet klienta:</b> {getattr(order, 'budget', 'N/A')} zł\n"
                    f"💵 <b>Twoja opłata:</b> {order.price} zł"
                )
            else:
                confirmation_text = f"✅ Przyjęte przez: {callback.from_user.full_name}"

            await callback.message.answer(
                text=confirmation_text,
                parse_mode="HTML"
            )

    except Exception as e:
        print(f"Błąd podczas akceptowania zamówienia: {e}")
        await callback.answer("Wystąpił błąd podczas przetwarzania zamówienia")


@router.message(F.location)
async def handle_driver_location(message: Message):
    """Handle driver's location updates"""
    with Session() as session:
        # Обновляем локацию водителя
        driver = session.query(DriverVehicle).filter_by(driver_id=message.from_user.id).first()
        if driver:
            # Проверяем, есть ли поля для локации в модели
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
                await Bots.client.send_location(
                    chat_id=order.user_id,
                    latitude=message.location.latitude,
                    longitude=message.location.longitude
                )
                await message.answer("Пассажир получил ваше местоположение")
            except Exception as e:
                print(f"Ошибка отправки локации пассажиру: {e}")


@router.callback_query(F.data.startswith("reject_"))
async def reject_order(callback: CallbackQuery):
    """Handle order rejection by driver"""
    try:
        order_id = int(callback.data.split("_")[1])

        with Session() as session:
            order = session.query(Order).get(order_id)
            if not order:
                await callback.answer("Zamówienie nie zostało znalezione!")
                return

            order.status = "rejected"
            session.commit()

            # Уведомляем клиента об отклонении
            rejection_message = (
                "❌ <b>Zamówienie odrzucone</b>\n\n"
                "Niestety, kierowca nie może zrealizować Twojego zamówienia.\n"
                "Szukamy innego dostępnego kierowcy..."
            )

            try:
                await Bots.client.send_message(
                    chat_id=order.user_id,
                    text=rejection_message,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Błąd wysyłania wiadomości do klienta: {e}")

        await callback.answer("Zamówienie odrzucone")
        await callback.message.edit_text(
            text=f"{callback.message.text}\n\n"
                 f"❌ <b>ODRZUCONE</b> przez: {callback.from_user.full_name}",
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Błąd podczas odrzucania zamówienia: {e}")
        await callback.answer("Wystąpił błąд podczas przetwarzania zamówienia")