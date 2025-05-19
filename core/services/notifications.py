from aiogram import Bot
from config import Config
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.models import Session, Order

async def notify_driver(bot: Bot, order_id: int):
    driver_chat_id = Config.DRIVER_CHAT_ID

    with Session() as session:
        order = session.query(Order).get(order_id)
        text = (
            "🚖 Новый заказ!\n"
            f"Тип: {order.order_type}\n"
            f"Дистанция: {order.distance} км\n"
            f"Стоимость: {order.price} zł\n"
            f"Ночной тариф: {'Да' if order.is_night else 'Нет'}"
        )

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Принять", callback_data=f"accept_{order_id}")
        keyboard.button(text="❌ Отклонить", callback_data=f"reject_{order_id}")

        await bot.send_message(
            chat_id=driver_chat_id,
            text=text,
            reply_markup=keyboard.as_markup()
        )