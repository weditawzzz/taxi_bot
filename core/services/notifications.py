from core.bot_instance import Bots
from core.models import Session, Order
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import Config


async def notify_driver(order_id: int):
    with Session() as session:
        order = session.query(Order).get(order_id)

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Przyjmij", callback_data=f"accept_{order_id}")
        builder.button(text="❌ Odrzuć", callback_data=f"reject_{order_id}")

        if order.order_type == "alcohol":
            text = (
                "🍾 <b>Nowe zamówienie alkoholu!</b>\n\n"
                f"📋 {order.destination}\n"
                f"📝 Produkty: {order.products}\n"
                f"💵 20 zł (dostawa) + paragon\n\n"
                "ℹ️ <i>Wymagane:\n"
                "1. Weryfikacja wieku\n"
                "2. Paragon fiskalny\n"
                "3. Pokwitowanie odbioru</i>"
            )
        else:
            text = (
                "🚖 <b>Nowe zamówienie!</b>\n\n"
                f"Typ: {order.order_type}\n"
                f"Z: {order.origin}\n"
                f"Do: {order.destination}\n"
                f"Dystans: {order.distance} km\n"
                f"Cena: {order.price} zł\n"
                f"Płatność: {order.payment_method}"
            )

        await Bots.driver.send_message(
            chat_id=Config.DRIVER_CHAT_ID,
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )