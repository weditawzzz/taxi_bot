from aiogram import Router, F
from aiogram.types import CallbackQuery
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
            arrival_time = "~15 minut" if order.order_type == "alcohol" else "~10 minut"

            session.commit()

            if order.order_type == "alcohol":
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
                message_text = (
                    "✅ <b>Kierowca zaakceptował Twoje zamówienie!</b>\n\n"
                    f"👤 Kierowca: {callback.from_user.full_name}\n"
                    f"🚗 Samochód: {car_info}\n"
                    f"🕒 Czas dojazdu: {arrival_time}\n\n"
                    f"💵 Do zapłaty: {order.price} zł ({order.payment_method})"
                )

            try:
                await Bots.client.send_message(
                    chat_id=order.user_id,
                    text=message_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Błąd wysyłania wiadomości do klienta: {e}")

        await callback.answer("Zamówienie zaakceptowane!")
        await callback.message.edit_text(
            text=f"{callback.message.text}\n\n"
                 f"✅ Przyjęte przez: {callback.from_user.full_name}"
        )

    except Exception as e:
        print(f"Błąd podczas akceptowania zamówienia: {e}")
        await callback.answer("Wystąpił błąd podczas przetwarzania zamówienia")


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

            try:
                await Bots.client.send_message(
                    chat_id=order.user_id,
                    text="❌ Niestety, kierowca odrzucił Twoje zamówienie. "
                         "Szukamy innego kierowcy...",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Błąd wysyłania wiadomości do klienta: {e}")

        await callback.answer("Zamówienie odrzucone")
        await callback.message.edit_text(
            text=f"{callback.message.text}\n\n"
                 f"❌ Odrzucone przez: {callback.from_user.full_name}"
        )

    except Exception as e:
        print(f"Błąd podczas odrzucania zamówienia: {e}")
        await callback.answer("Wystąpił błąd podczas przetwarzania zamówienia")