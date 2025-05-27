"""
Обработчик заказов алкоголя (покупка и доставка из магазинов)
"""
import logging
import sys
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Добавляем корневую папку в путь для импорта states
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from core.states import AlcoholOrderState
except ImportError:
    # Fallback - создаем состояния локально
    from aiogram.fsm.state import State, StatesGroup

    class AlcoholOrderState(StatesGroup):
        waiting_products = State()
        waiting_budget = State()
        waiting_age = State()
        waiting_address = State()
        confirmation = State()

from config import Config
from core.services.user_service import UserService
from core.models import User, Ride, RideStatus
from core.database import get_session

logger = logging.getLogger(__name__)
router = Router()


# Функции локализации
def get_localization(lang: str, key: str) -> str:
    """Функция локализации с поддержкой всех языков"""
    translations = {
        "pl": {
            "start": "👋 Witaj! Wybierz usługę:",
            "enter_shopping_list": "🛒 Wprowadź listę zakupów (np. 1x Żubr 0.5L, 2x Żywiec, 1x Vodka):",
            "enter_budget": "💰 Podaj maksymalny budżet na zakupy (w zł):",
            "invalid_budget": "❌ Nieprawidłowy budżet! Wprowadź liczbę:",
            "budget_too_low": "❌ Minimalna kwota zakupów to 20 zł",
            "confirm_age": "🔞 Czy masz ukończone 18 lat?",
            "age_warning": "🚫 Dostawa alkoholu możliwa tylko dla osób pełnoletnich!",
            "enter_alcohol_address": "📍 Podaj adres dostawy:",
            "alcohol_shop_tariff_info": "🚚 <b>Dostawa alkoholu:</b>\n\n• Stała opłata: 20 zł\n• Dostawa w ciągu 60 minut\n• Płatność <u>wyłącznie gotówką</u>",
            "alcohol_cash_only": "⚠️ <b>Uwaga!</b> Przy dostawie alkoholu możliwa jest <u>wyłącznie płatność gotówką</u>!",
            "alcohol_shop_receipt_info": "📝 <b>Uwaga!</b> Kierowca przywiezie paragon za alkohol, który należy opłacić <u>dodatkowo</u> do kosztów dostawy.",
            "back_to_menu": "↩️ Wróć do menu",
            "route_error": "❌ Błąd trasy. Sprawdź adresy.",
            "yes": "✔ Tak",
            "no": "✖ Nie",
            "alcohol_service_description": "🛒 <b>Usługa zakupu i dostawy alkoholu</b>\n\nKierowca kupi alkohol zgodnie z Twoją listą i dostawi pod wskazany adres.",
            "alcohol_order_waiting": "🕒 <b>Zamówienie oczekuje na akceptację przez kierowcę</b>\n\nPo akceptacji otrzymasz:\n- Dane kierowcy i pojazdu\n- Szacowany czas realizacji",
            "order_cancelled": "❌ <b>Zamówienie anulowane</b>",
            "order_error": "❌ <b>Błąd podczas tworzenia zamówienia</b>",
            "start": "👋 Witaj! Wybierz usługę:"
        },
        "ru": {
            "start": "👋 Добро пожаловать! Выберите услугу:",
            "enter_shopping_list": "🛒 Введите список покупок (напр. 1x Пиво 0.5Л, 2x Водка, 1x Вино):",
            "enter_budget": "💰 Укажите максимальный бюджет на покупки (в zł):",
            "invalid_budget": "❌ Неверный бюджет! Введите число:",
            "budget_too_low": "❌ Минимальная сумма покупок 20 zł",
            "confirm_age": "🔞 Вам есть 18 лет?",
            "age_warning": "🚫 Доставка алкоголя только для совершеннолетних!",
            "enter_alcohol_address": "📍 Укажите адрес доставки:",
            "alcohol_shop_tariff_info": "🚚 <b>Доставка алкоголя:</b>\n\n• Фиксированная плата: 20 zł\n• Доставка в течение 60 минут\n• Оплата <u>только наличными</u>",
            "alcohol_cash_only": "⚠️ <b>Внимание!</b> При доставке алкоголя возможна <u>только оплата наличными</u>!",
            "alcohol_shop_receipt_info": "📝 <b>Внимание!</b> Водитель привезет чек за алкоголь, который нужно оплатить <u>дополнительно</u> к стоимости доставки.",
            "back_to_menu": "↩️ Назад в меню",
            "route_error": "❌ Ошибка маршрута. Проверьте адреса.",
            "yes": "✔ Да",
            "no": "✖ Нет",
            "alcohol_service_description": "🛒 <b>Услуга покупки и доставки алкоголя</b>\n\nВодитель купит алкоголь согласно вашему списку и доставит по указанному адресу.",
            "alcohol_order_waiting": "🕒 <b>Заказ ожидает принятия водителем</b>\n\nПосле подтверждения вы получите:\n- Данные водителя и автомобиля\n- Примерное время выполнения",
            "order_cancelled": "❌ <b>Заказ отменен</b>",
            "order_error": "❌ <b>Ошибка при создании заказа</b>",
            "start": "👋 Добро пожаловать! Выберите услугу:"
        },
        "en": {
            "start": "👋 Hello! Choose service:",
            "enter_shopping_list": "🛒 Enter shopping list (e.g. 1x Beer 0.5L, 2x Vodka, 1x Wine):",
            "enter_budget": "💰 Enter maximum budget for purchases (in zł):",
            "invalid_budget": "❌ Invalid budget! Enter a number:",
            "budget_too_low": "❌ Minimum purchase amount is 20 zł",
            "confirm_age": "🔞 Are you 18+ years old?",
            "age_warning": "🚫 Alcohol delivery only for adults!",
            "enter_alcohol_address": "📍 Enter delivery address:",
            "alcohol_shop_tariff_info": "🚚 <b>Alcohol delivery:</b>\n\n• Fixed fee: 20 zł\n• Delivery within 60 minutes\n• Payment <u>cash only</u>",
            "alcohol_cash_only": "⚠️ <b>Attention!</b> For alcohol delivery <u>only cash payment</u> is possible!",
            "alcohol_shop_receipt_info": "📝 <b>Attention!</b> Driver will bring receipt for alcohol that must be paid <u>additionally</u> to delivery cost.",
            "back_to_menu": "↩️ Back to menu",
            "route_error": "❌ Route error. Check addresses.",
            "yes": "✔ Yes",
            "no": "✖ No",
            "alcohol_service_description": "🛒 <b>Alcohol purchase and delivery service</b>\n\nDriver will buy alcohol according to your list and deliver to specified address.",
            "alcohol_order_waiting": "🕒 <b>Order awaiting driver acceptance</b>\n\nAfter confirmation you will receive:\n- Driver and vehicle details\n- Estimated completion time",
            "order_cancelled": "❌ <b>Order cancelled</b>",
            "order_error": "❌ <b>Error creating order</b>",
            "start": "👋 Hello! Choose service:"
        }
    }
    return translations.get(lang, {}).get(key, key)


async def get_user_language(telegram_id: int) -> str:
    """Получить язык пользователя"""
    try:
        user_service = UserService()
        user = await user_service.get_user_by_telegram_id(telegram_id)
        return user.language if user and user.language else "pl"
    except Exception:
        return "pl"


# Клавиатуры
def confirm_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_localization(lang, "yes"), callback_data="confirm_yes")
    builder.button(text=get_localization(lang, "no"), callback_data="confirm_no")
    return builder.as_markup()


def back_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_localization(lang, "back_to_menu"), callback_data="back_to_menu")
    return builder.as_markup()





# Функции расчета
def calculate_distance(origin: str, destination: str) -> float:
    """Примерный расчет расстояния"""
    # TODO: Интегрировать с Google Maps API
    return 5.0


def calculate_alcohol_delivery_price(distance: float) -> float:
    """Расчет цены доставки алкоголя - фиксированная ставка"""
    return 20.0  # Фиксированная цена 20 zł


async def save_alcohol_order(user_id: int, order_data: dict) -> int:
    """Сохранить заказ алкоголя"""
    try:
        async with get_session() as session:
            # Используем модель Ride как основу для заказа
            ride = Ride(
                client_id=user_id,
                pickup_address="Alcohol Shop Delivery",
                pickup_lat=53.4285,  # Координаты Щецина
                pickup_lng=14.5528,
                destination_address=order_data['address'],
                destination_lat=53.4285,  # Примерные координаты
                destination_lng=14.5528,
                distance_km=order_data.get('distance', 5.0),
                estimated_price=order_data['price'],
                status=RideStatus.PENDING,
                notes=f"ALCOHOL DELIVERY - Products: {order_data['products']}, Budget: {order_data['budget']} zł"
            )

            session.add(ride)
            await session.commit()
            await session.refresh(ride)

            logger.info(f"Alcohol order saved: {ride.id}")
            return ride.id

    except Exception as e:
        logger.error(f"Error saving alcohol order: {e}")
        return 1  # Fallback ID


async def notify_driver_simple(order_id: int, order_data: dict):
    """Простое уведомление водителя без списка магазинов"""
    try:
        from core.bot_instance import Bots

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Przyjmij", callback_data=f"accept_{order_id}")
        builder.button(text="❌ Odrzuć", callback_data=f"reject_{order_id}")

        text = (
            "🛒 <b>ZAKUP I DOSTAWA ALKOHOLU</b>\n\n"
            f"📝 <b>Lista zakupów:</b>\n{order_data['products']}\n\n"
            f"💰 <b>Budżet klienta:</b> {order_data['budget']} zł\n"
            f"📍 <b>Dostawa na:</b> {order_data['address']}\n"
            f"📏 <b>Odległość:</b> ~{order_data.get('distance', 5):.1f} km\n"
            f"💵 <b>Twoja opłata:</b> {order_data['price']} zł\n\n"
            f"ℹ️ <b>Instrukcje:</b>\n"
            f"1. Wybierz najbliższy sklep z alkoholem\n"
            f"2. Kup produkty zgodnie z listą\n"
            f"3. Zachowaj paragon fiskalny!\n"
            f"4. Dostarcz + sprawdź dokumenty (18+)\n"
            f"5. Odbierz: {order_data['price']} zł + koszt zakupów"
        )

        await Bots.driver.send_message(
            chat_id=Config.DRIVER_CHAT_ID,
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error notifying driver: {e}")


# Обработчики callback-ов от главного меню
@router.callback_query(F.data == "confirm_yes", AlcoholOrderState.waiting_products)
async def handle_confirm_yes_start_order(callback: CallbackQuery, state: FSMContext):
    """Обработка подтверждения начала заказа алкоголя"""
    lang = await get_user_language(callback.from_user.id)

    await callback.message.answer(
        text=get_localization(lang, "enter_shopping_list"),
        reply_markup=back_keyboard(lang)
    )
    await state.set_state(AlcoholOrderState.waiting_budget)


@router.callback_query(F.data == "confirm_yes", AlcoholOrderState.confirmation)
async def handle_confirm_yes_final(callback: CallbackQuery, state: FSMContext):
    """Обработка финального подтверждения заказа"""
    await confirm_alcohol_order(callback, state)


@router.callback_query(F.data == "confirm_no")
async def handle_confirm_no_from_menu(callback: CallbackQuery, state: FSMContext):
    """Обработка отмены из главного меню"""
    await cancel_order(callback, state)


@router.callback_query(F.data == "menu_alcohol")
async def start_alcohol_order(callback: CallbackQuery, state: FSMContext):
    """Начало заказа алкоголя"""
    lang = await get_user_language(callback.from_user.id)

    await callback.message.edit_text(
        text=get_localization(lang, "alcohol_service_description"),
        parse_mode="HTML",
        reply_markup=confirm_keyboard(lang)
    )
    await state.set_state(AlcoholOrderState.waiting_products)





@router.message(AlcoholOrderState.waiting_budget)
async def process_shopping_list(message: Message, state: FSMContext):
    """Обработка списка покупок"""
    lang = await get_user_language(message.from_user.id)

    if message.text == get_localization(lang, "back_to_menu"):
        await state.clear()

        from core.keyboards import get_main_menu_keyboard
        from core.models import UserRole

        keyboard = get_main_menu_keyboard(lang, UserRole.CLIENT)

        await message.answer(
            text=get_localization(lang, "start"),
            reply_markup=keyboard
        )
        return

    await state.update_data(products=message.text)
    await message.answer(
        text=get_localization(lang, "enter_budget"),
        reply_markup=back_keyboard(lang)
    )
    await state.set_state(AlcoholOrderState.waiting_age)


@router.message(AlcoholOrderState.waiting_age)
async def process_budget(message: Message, state: FSMContext):
    """Обработка бюджета"""
    lang = await get_user_language(message.from_user.id)

    if message.text == get_localization(lang, "back_to_menu"):
        await state.clear()

        from core.keyboards import get_main_menu_keyboard
        from core.models import UserRole

        keyboard = get_main_menu_keyboard(lang, UserRole.CLIENT)

        await message.answer(
            text=get_localization(lang, "start"),
            reply_markup=keyboard
        )
        return

    try:
        budget = float(message.text)
        if budget < 20:
            await message.answer(get_localization(lang, "budget_too_low"))
            return

        await state.update_data(budget=budget)
        await message.answer(
            text=get_localization(lang, "confirm_age"),
            reply_markup=confirm_keyboard(lang)
        )
        await state.set_state(AlcoholOrderState.waiting_address)

    except ValueError:
        await message.answer(get_localization(lang, "invalid_budget"))


@router.callback_query(AlcoholOrderState.waiting_address, F.data.startswith("confirm_"))
async def process_age_confirmation(callback: CallbackQuery, state: FSMContext):
    """Подтверждение возраста"""
    lang = await get_user_language(callback.from_user.id)
    is_adult = callback.data.split("_")[1] == "yes"

    if not is_adult:
        # Если несовершеннолетний, возвращаем в главное меню
        await state.clear()

        # Сначала редактируем текущее сообщение
        await callback.message.edit_text(
            text=get_localization(lang, "age_warning"),
            parse_mode="HTML"
        )

        # Затем отправляем новое сообщение с главным меню
        from core.keyboards import get_main_menu_keyboard
        from core.models import UserRole

        keyboard = get_main_menu_keyboard(lang, UserRole.CLIENT)

        await callback.message.answer(
            text=get_localization(lang, "start"),
            reply_markup=keyboard
        )
        return

    await callback.message.answer(
        text=get_localization(lang, "alcohol_shop_tariff_info"),
        parse_mode="HTML"
    )

    await callback.message.answer(
        text=get_localization(lang, "enter_alcohol_address"),
        reply_markup=back_keyboard(lang)
    )
    await state.set_state(AlcoholOrderState.confirmation)


@router.message(AlcoholOrderState.confirmation)
async def process_delivery_address(message: Message, state: FSMContext):
    """Обработка адреса доставки"""
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()

    if message.text == get_localization(lang, "back_to_menu"):
        await state.clear()

        from core.keyboards import get_main_menu_keyboard
        from core.models import UserRole

        keyboard = get_main_menu_keyboard(lang, UserRole.CLIENT)

        await message.answer(
            text=get_localization(lang, "start"),
            reply_markup=keyboard
        )
        return

    try:
        distance = calculate_distance("Plac Żołnierza, Szczecin", message.text)
        price = calculate_alcohol_delivery_price(distance)

        await state.update_data(address=message.text, distance=distance, price=price)

        await message.answer(
            text=get_localization(lang, "alcohol_cash_only") + "\n\n" +
                 get_localization(lang, "alcohol_shop_receipt_info"),
            parse_mode="HTML"
        )

        # Используем локализованные строки для заказа
        if lang == "pl":
            order_text = (
                f"🍾 <b>Dostawa alkoholu</b>\n\n"
                f"📋 <b>Lista zakupów:</b>\n<i>{data['products']}</i>\n\n"
                f"💰 <b>Budżet na zakupy:</b> {data['budget']} zł\n"
                f"🏠 <b>Adres dostawy:</b>\n{message.text}\n"
                f"📏 <b>Odległość:</b> ~{distance:.1f} km\n\n"
                f"💵 <b>Opłata za dostawę:</b> 20 zł\n"
                f"💵 <b>+ koszt zakupów</b> (do {data['budget']} zł)\n\n"
                f"💰 <b>Płatność:</b> gotówka\n"
                f"🕒 <b>Czas realizacji:</b> 30-45 minut"
            )
        elif lang == "ru":
            order_text = (
                f"🍾 <b>Доставка алкоголя</b>\n\n"
                f"📋 <b>Список покупок:</b>\n<i>{data['products']}</i>\n\n"
                f"💰 <b>Бюджет на покупки:</b> {data['budget']} zł\n"
                f"🏠 <b>Адрес доставки:</b>\n{message.text}\n"
                f"📏 <b>Расстояние:</b> ~{distance:.1f} км\n\n"
                f"💵 <b>Плата за доставку:</b> 20 zł\n"
                f"💵 <b>+ стоимость покупок</b> (до {data['budget']} zł)\n\n"
                f"💰 <b>Оплата:</b> наличные\n"
                f"🕒 <b>Время выполнения:</b> 30-45 минут"
            )
        else:  # en
            order_text = (
                f"🍾 <b>Alcohol delivery</b>\n\n"
                f"📋 <b>Shopping list:</b>\n<i>{data['products']}</i>\n\n"
                f"💰 <b>Shopping budget:</b> {data['budget']} zł\n"
                f"🏠 <b>Delivery address:</b>\n{message.text}\n"
                f"📏 <b>Distance:</b> ~{distance:.1f} km\n\n"
                f"💵 <b>Delivery fee:</b> 20 zł\n"
                f"💵 <b>+ purchase cost</b> (up to {data['budget']} zł)\n\n"
                f"💰 <b>Payment:</b> cash\n"
                f"🕒 <b>Completion time:</b> 30-45 minutes"
            )

        await message.answer(
            text=order_text,
            parse_mode="HTML",
            reply_markup=confirm_keyboard(lang)
        )

    except Exception as e:
        logger.error(f"Error processing address: {e}")
        await message.answer(get_localization(lang, "route_error"))


@router.callback_query(F.data.startswith("confirm_"), AlcoholOrderState.confirmation)
async def confirm_alcohol_order(callback: CallbackQuery, state: FSMContext):
    """Подтверждение заказа"""
    lang = await get_user_language(callback.from_user.id)
    action = callback.data.split("_")[1]

    if action == "yes":
        data = await state.get_data()

        try:
            order_id = await save_alcohol_order(callback.from_user.id, data)
            await notify_driver_simple(order_id, data)

            await callback.message.edit_text(
                text=get_localization(lang, "alcohol_order_waiting"),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error confirming order: {e}")
            await callback.message.edit_text(
                text=get_localization(lang, "order_error"),
                parse_mode="HTML"
            )
    else:
        await callback.message.edit_text(
            text=get_localization(lang, "order_cancelled"),
            parse_mode="HTML"
        )

    await state.clear()


@router.callback_query(F.data == "confirm_no")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    """Отмена заказа"""
    lang = await get_user_language(callback.from_user.id)
    await state.clear()

    # Сначала редактируем текущее сообщение без клавиатуры
    await callback.message.edit_text(
        text=get_localization(lang, "order_cancelled"),
        parse_mode="HTML"
    )

    # Затем отправляем новое сообщение с главным меню
    from core.keyboards import get_main_menu_keyboard
    from core.models import UserRole

    keyboard = get_main_menu_keyboard(lang, UserRole.CLIENT)

    await callback.message.answer(
        text=get_localization(lang, "start"),
        reply_markup=keyboard
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    lang = await get_user_language(callback.from_user.id)

    # Сначала редактируем текущее сообщение без клавиатуры
    await callback.message.edit_text(
        text=get_localization(lang, "start")
    )

    # Затем отправляем новое сообщение с главным меню
    from core.keyboards import get_main_menu_keyboard
    from core.models import UserRole

    keyboard = get_main_menu_keyboard(lang, UserRole.CLIENT)

    await callback.message.answer(
        text=get_localization(lang, "start"),
        reply_markup=keyboard
    )