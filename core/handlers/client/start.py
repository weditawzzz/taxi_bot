"""
Хэндлеры для клиентского бота - начальные команды
"""
import logging
from typing import Optional

from aiogram import types, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from core.handlers.client.alcohol import router as alcohol_router
from core.services import UserService
from core.models import UserRole
from core.exceptions import TaxiBotException, ValidationError, NotFoundError
from core.utils.localization import get_text, Language
from core.keyboards import get_main_menu_keyboard, get_language_keyboard
from core.states import ClientStates

logger = logging.getLogger(__name__)

# Роутер для клиентских хэндлеров
client_router = Router()

# Создаем сервисы
user_service = UserService()


async def get_user_language(telegram_id: int) -> Language:
    """Получить язык пользователя"""
    try:
        user = await user_service.get_user_by_telegram_id(telegram_id)
        if user and user.language in ['en', 'pl', 'ru']:
            return Language(user.language)
        return Language.PL  # Польский по умолчанию для Щецина
    except Exception as e:
        logger.error(f"Error getting user language: {e}")
        return Language.PL


async def handle_error(
    update: types.Update,
    error: Exception,
    user_id: int,
    default_message: str = "Произошла ошибка. Попробуйте позже."
) -> None:
    """Обработка ошибок"""
    try:
        language = await get_user_language(user_id)

        if isinstance(error, ValidationError):
            message = get_text("validation_error", language, error=str(error))
        elif isinstance(error, NotFoundError):
            message = get_text("not_found_error", language)
        elif isinstance(error, TaxiBotException):
            message = get_text("service_error", language)
        else:
            logger.error(f"Unexpected error: {error}", exc_info=True)
            message = get_text("unexpected_error", language)

        if isinstance(update, Message):
            await update.answer(message)
        elif isinstance(update, CallbackQuery):
            await update.message.answer(message)
            await update.answer()

    except Exception as e:
        logger.error(f"Error in error handler: {e}")
        try:
            if isinstance(update, Message):
                await update.answer(default_message)
            elif isinstance(update, CallbackQuery):
                await update.message.answer(default_message)
                await update.answer()
        except:
            pass


@client_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Команда /start"""
    try:
        # Очищаем состояние
        await state.clear()

        # Создаем или обновляем пользователя
        user = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            role=UserRole.CLIENT
        )

        language = await get_user_language(message.from_user.id)

        welcome_text = get_text(
            "welcome_client",
            language,
            name=user.first_name or "Friend"
        )

        keyboard = get_main_menu_keyboard(language.value, UserRole.CLIENT)

        await message.answer(
            welcome_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    except Exception as e:
        await handle_error(message, e, message.from_user.id)


@client_router.message(F.text.in_(["🚖 Zamów taxi", "🚖 Заказать такси", "🚖 Order Taxi"]))
async def order_taxi(message: Message, state: FSMContext) -> None:
    """Начать процесс заказа такси"""
    try:
        language = await get_user_language(message.from_user.id)

        text = get_text("send_pickup_location", language)

        # Импортируем здесь чтобы избежать циклических импортов
        from core.keyboards import get_location_keyboard
        keyboard = get_location_keyboard(language.value)

        await message.answer(text, reply_markup=keyboard)
        await state.set_state(ClientStates.WAITING_PICKUP_LOCATION)

    except Exception as e:
        await handle_error(message, e, message.from_user.id)


@client_router.message(F.text.in_(["🍷 Dostawa alkoholu", "🍷 Доставка алкоголя", "🍷 Alcohol Delivery"]))
async def order_alcohol(message: Message, state: FSMContext) -> None:
    """Начать процесс заказа алкоголя без показа списка магазинов"""
    try:
        # Получаем язык пользователя
        language = await get_user_language(message.from_user.id)

        # Локализованные тексты
        alcohol_texts = {
            Language.PL: {
                'service_info': '🛒 <b>Usługa zakupu i dostawy alkoholu</b>\n\nKierowca kupi alkohol zgodnie z Twoją listą i dostawi pod wskazany adres.',
                'confirm_yes': '✔ Tak',
                'confirm_no': '✖ Nie'
            },
            Language.RU: {
                'service_info': '🛒 <b>Услуга покупки и доставки алкоголя</b>\n\nВодитель купит алкоголь согласно вашему списку и доставит по указанному адресу.',
                'confirm_yes': '✔ Да',
                'confirm_no': '✖ Нет'
            },
            Language.EN: {
                'service_info': '🛒 <b>Alcohol purchase and delivery service</b>\n\nDriver will buy alcohol according to your list and deliver to specified address.',
                'confirm_yes': '✔ Yes',
                'confirm_no': '✖ No'
            }
        }

        # Берем тексты для текущего языка
        texts = alcohol_texts.get(language, alcohol_texts[Language.PL])

        # Создаем инлайн-клавиатуру
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text=texts['confirm_yes'], callback_data="confirm_yes")
        builder.button(text=texts['confirm_no'], callback_data="confirm_no")

        await message.answer(
            text=texts['service_info'],
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )

        # Импортируем состояния алкоголя
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from states import AlcoholOrderState
            await state.set_state(AlcoholOrderState.waiting_products)
        except ImportError:
            # Fallback - создаем состояние локально
            from aiogram.fsm.state import State, StatesGroup

            class AlcoholOrderState(StatesGroup):
                waiting_products = State()
                waiting_budget = State()
                waiting_age = State()
                waiting_address = State()
                confirmation = State()

            await state.set_state(AlcoholOrderState.waiting_products)

    except Exception as e:
        logger.error(f"Error starting alcohol order: {e}")
        await message.answer("⚠️ Модуль доставки алкоголя временно недоступен")


@client_router.message(F.text.in_(["📋 Moje przejazdy", "📋 Мои поездки", "📋 My Rides"]))
async def my_rides(message: Message) -> None:
    """Показать историю поездок"""
    try:
        language = await get_user_language(message.from_user.id)

        text = get_text("rides_history", language)
        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        await handle_error(message, e, message.from_user.id)


@client_router.message(F.text.in_(["⚙️ Ustawienia", "⚙️ Настройки", "⚙️ Settings"]))
async def settings(message: Message) -> None:
    """Настройки пользователя"""
    try:
        language = await get_user_language(message.from_user.id)

        text = get_text("settings_menu", language)
        keyboard = get_language_keyboard()

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        await handle_error(message, e, message.from_user.id)


@client_router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery) -> None:
    """Установка языка"""
    try:
        lang_code = callback.data.split("_")[1]

        await user_service.update_user_language(
            callback.from_user.id,
            lang_code
        )

        new_language = Language(lang_code)
        success_text = get_text("language_changed", new_language)

        await callback.message.edit_text(success_text)
        await callback.answer()

        # Обновляем главное меню с новым языком
        main_keyboard = get_main_menu_keyboard(new_language.value, UserRole.CLIENT)
        await callback.message.answer(
            get_text("main_menu", new_language),
            reply_markup=main_keyboard
        )

    except Exception as e:
        await handle_error(callback, e, callback.from_user.id)


@client_router.message(F.text.in_(["ℹ️ Pomoc", "ℹ️ Помощь", "ℹ️ Help"]))
async def help_command(message: Message) -> None:
    """Помощь"""
    try:
        language = await get_user_language(message.from_user.id)

        if language == Language.EN:
            help_text = """
ℹ️ <b>Help</b>

<b>How to order a taxi:</b>
1. Press "🚖 Order Taxi"
2. Send your location or enter pickup address
3. Enter destination
4. Choose number of passengers
5. Confirm the order

<b>How to order alcohol delivery:</b>
1. Press "🍷 Alcohol Delivery"
2. Enter shopping list
3. Set budget (min 20 zł)
4. Confirm age (18+) and address

<b>Other features:</b>
• 📋 View ride history
• ⚙️ Change language and settings
• ℹ️ Get help

<b>Support:</b> @taxi_support_bot
"""
        elif language == Language.RU:
            help_text = """
ℹ️ <b>Помощь</b>

<b>Как заказать такси:</b>
1. Нажмите "🚖 Заказать такси"
2. Отправьте локацию или введите адрес подачи
3. Введите место назначения
4. Выберите количество пассажиров
5. Подтвердите заказ

<b>Как заказать доставку алкоголя:</b>
1. Нажмите "🍷 Доставка алкоголя"
2. Введите список покупок
3. Укажите бюджет (мин 20 zł)
4. Подтвердите возраст (18+) и адрес

<b>Другие функции:</b>
• 📋 Просмотр истории поездок
• ⚙️ Смена языка и настройки
• ℹ️ Получить помощь

<b>Поддержка:</b> @taxi_support_bot
"""
        else:  # Polish
            help_text = """
ℹ️ <b>Pomoc</b>

<b>Jak zamówić taxi:</b>
1. Naciśnij "🚖 Zamów taxi"  
2. Wyślij lokalizację lub wpisz adres odbioru
3. Wpisz miejsce docelowe
4. Wybierz liczbę pasażerów
5. Potwierdź zamówienie

<b>Jak zamówić dostawę alkoholu:</b>
1. Naciśnij "🍷 Dostawa alkoholu"
2. Wpisz listę zakupów
3. Ustaw budżet (min 20 zł)
4. Potwierdź wiek (18+) i adres

<b>Inne funkcje:</b>
• 📋 Przeglądanie historii przejazdów
• ⚙️ Zmiana języka i ustawień
• ℹ️ Uzyskaj pomoc

<b>Wsparcie:</b> @taxi_support_bot
"""

        await message.answer(help_text, parse_mode="HTML")

    except Exception as e:
        await handle_error(message, e, message.from_user.id)