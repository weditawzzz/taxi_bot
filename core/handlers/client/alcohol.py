from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from core.bot_instance import Bots
bot = Bots.client
from core.models import Session, Order
from core.services.user_service import get_localization, get_user_language
from core.states import AlcoholOrderState
from core.keyboards import confirm_keyboard, back_keyboard, main_menu_keyboard
from core.services.notifications import notify_driver
# Удалите старый импорт бота, если он есть

router = Router()


@router.callback_query(F.data == "menu_alcohol")
async def start_alcohol_order(callback: CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        text=get_localization(lang, "enter_alcohol_list"),
        reply_markup=back_keyboard(lang)
    )
    await state.set_state(AlcoholOrderState.waiting_products)


@router.message(AlcoholOrderState.waiting_products)
async def process_products(message: Message, state: FSMContext):
    lang = get_user_language(message.from_user.id)

    if message.text == get_localization(lang, "back"):
        await state.clear()
        await message.answer(
            text=get_localization(lang, "start"),
            reply_markup=main_menu_keyboard(lang)
        )
        return

    await state.update_data(products=message.text)
    await message.answer(
        text=get_localization(lang, "confirm_age"),
        reply_markup=confirm_keyboard(lang)
    )
    await state.set_state(AlcoholOrderState.waiting_age)


@router.callback_query(AlcoholOrderState.waiting_age, F.data.startswith("confirm_"))
async def process_age_confirmation(callback: CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    is_adult = callback.data.split("_")[1] == "yes"

    if not is_adult:
        await callback.message.edit_text(get_localization(lang, "age_warning"))
        await state.clear()
        return

    # Отправляем информацию о тарифе
    await callback.message.answer(
        text=get_localization(lang, "alcohol_tariff_info"),
        parse_mode="HTML"
    )

    # Запрашиваем адрес доставки
    await callback.message.answer(
        text=get_localization(lang, "enter_alcohol_address"),
        reply_markup=back_keyboard(lang)
    )
    await state.set_state(AlcoholOrderState.waiting_address)


@router.message(AlcoholOrderState.waiting_address)
async def process_address(message: Message, state: FSMContext):
    lang = get_user_language(message.from_user.id)
    data = await state.get_data()

    # Уведомление об оплате наличными
    await message.answer(
        text=get_localization(lang, "alcohol_cash_only") + "\n\n" +
             get_localization(lang, "alcohol_receipt_info"),
        parse_mode="HTML"
    )

    # Сохраняем адрес доставки
    await state.update_data(address=message.text)

    # Формируем итоговое сообщение
    order_text = (
        f"🍾 <b>Zamówienie alkoholu:</b>\n"
        f"📋 <i>{data['products']}</i>\n\n"
        f"🏠 <b>Adres dostawy:</b>\n{message.text}\n\n"
        f"💵 <b>Do zapłaty:</b> 20 zł (gotówka)"
    )

    await message.answer(
        text=order_text,
        parse_mode="HTML",
        reply_markup=confirm_keyboard(lang)
    )
    await state.set_state(AlcoholOrderState.confirmation)


@router.callback_query(F.data == "step_back", AlcoholOrderState.waiting_age)
async def back_to_products(callback: CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        text=get_localization(lang, "enter_alcohol_list"),
        reply_markup=back_keyboard(lang)
    )
    await state.set_state(AlcoholOrderState.waiting_products)


@router.callback_query(F.data.startswith("confirm_"), AlcoholOrderState.confirmation)
async def confirm_alcohol_order(callback: CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    action = callback.data.split("_")[1]

    if action == "yes":
        data = await state.get_data()

        with Session() as session:
            order = Order(
                user_id=callback.from_user.id,
                order_type="alcohol",
                destination=data['address'],
                products=data['products'],
                price=20.0,
                payment_method="cash",
                status="waiting"  # Изменено на "waiting"
            )
            session.add(order)
            session.commit()

            await notify_driver(order.id)

            await callback.message.edit_text(
                text="🕒 <b>Zamówienie oczekuje na akceptację przez kierowcę</b>\n\n"
                     "Po akceptacji otrzymasz:\n"
                     "- Dane kierowcy i pojazdu\n"
                     "- Szacowany czas przyjazdu",
                parse_mode="HTML"
            )

    await state.clear()