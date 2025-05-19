from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from config import Config
from core.services.user_service import get_or_create_user
from core.services.price_calculator import calculate_city_price
from core.keyboards import confirm_keyboard, payment_keyboard
from core.handlers.client.start import get_localization
from core.models import Session, Order, User
from core.services.notifications import notify_driver
from core.services.price_calculator import is_night_tariff
from client_bot import bot
from aiogram.fsm.state import State, StatesGroup
from core.services.maps_service import calculate_distance
from core.services.user_service import get_user_language  # Добавьте в начало файла
from aiogram.types import Message
from core.states import OrderState  # Убедитесь, что импорт есть
import logging


logger = logging.getLogger(__name__)
router = Router()


class OrderState(StatesGroup):
    waiting_origin = State()
    waiting_destination = State()
    confirmation = State()


@router.callback_query(F.data == "menu_city_ride")
async def handle_city_ride(callback: CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        text=get_localization(lang, "enter_origin"),
        reply_markup=None
    )
    await state.set_state(OrderState.waiting_origin)


@router.message(OrderState.waiting_origin)
async def process_origin(message: Message, state: FSMContext):
    formatted_address = f"{message.text}, {Config.DEFAULT_CITY}"
    await state.update_data(origin=formatted_address)
    lang = get_user_language(message.from_user.id)
    await message.answer(get_localization(lang, "enter_destination"))
    await state.set_state(OrderState.waiting_destination)


@router.message(OrderState.waiting_destination)
async def process_destination(message: Message, state: FSMContext):
    lang = get_user_language(message.from_user.id)
    data = await state.get_data()

    try:
        formatted_address = f"{message.text}, {Config.DEFAULT_CITY}"
        distance = calculate_distance(data['origin'], formatted_address)

        if distance > Config.MAX_CITY_DISTANCE_KM:
            await message.answer(get_localization(lang, "distance_too_long"))
            return

        await state.update_data(
            destination=formatted_address,
            distance=distance
        )

        # Запрашиваем способ оплаты
        await message.answer(
            get_localization(lang, "select_payment"),
            reply_markup=payment_keyboard(lang)
        )
        await state.set_state(OrderState.waiting_payment)

    except Exception as e:
        await message.answer(get_localization(lang, "route_error"))
        logging.error(f"Route error: {e}")


@router.callback_query(F.data.startswith("payment_"), OrderState.waiting_payment)
async def process_payment(callback: CallbackQuery, state: FSMContext):
    payment_method = callback.data.split("_")[1]  # cash или usdt
    lang = get_user_language(callback.from_user.id)

    await state.update_data(payment_method=payment_method)
    data = await state.get_data()

    # Рассчитываем окончательную цену
    price = calculate_city_price(data['distance'])
    await state.update_data(price=price)

    # Формируем информацию о заказе
    payment_info = get_localization(lang, f"payment_info_{payment_method}")

    await callback.message.edit_text(
        text=f"{get_localization(lang, 'route_info')}:\n"
             f"📍 {data['origin']} → {data['destination']}\n"
             f"📏 {data['distance']:.1f} km\n"
             f"💵 {price} zł\n"
             f"💳 {payment_info}\n\n"
             f"{get_localization(lang, 'confirm_order')}",
        reply_markup=confirm_keyboard(lang)
    )
    await state.set_state(OrderState.confirmation)


@router.callback_query(F.data.startswith("confirm_"), OrderState.confirmation)
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    data = await state.get_data()
    lang = get_user_language(callback.from_user.id)

    if action == "yes":
        with Session() as session:
            order = Order(
                user_id=callback.from_user.id,
                order_type="city",
                origin=data['origin'],
                destination=data['destination'],
                distance=data['distance'],
                price=data['price'],
                payment_method=data['payment_method'],  # Сохраняем способ оплаты
                is_night=is_night_tariff()
            )
            session.add(order)
            session.commit()

            await notify_driver(bot, order.id)
            await callback.message.edit_text(
                text=get_localization(lang, "order_created")
            )

    await state.clear()