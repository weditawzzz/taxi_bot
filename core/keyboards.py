"""
Клавиатуры для ботов
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
)
from .models import UserRole


def get_main_menu_keyboard(language: str = "pl", role: UserRole = UserRole.CLIENT) -> ReplyKeyboardMarkup:
    """Главное меню"""

    if role == UserRole.CLIENT:
        if language == "en":
            buttons = [
                [KeyboardButton(text="🚖 Order Taxi")],
                [KeyboardButton(text="🍷 Alcohol Delivery")],  # Новая кнопка
                [KeyboardButton(text="📋 My Rides"), KeyboardButton(text="⚙️ Settings")],
                [KeyboardButton(text="ℹ️ Help")]
            ]
        elif language == "ru":
            buttons = [
                [KeyboardButton(text="🚖 Заказать такси")],
                [KeyboardButton(text="🍷 Доставка алкоголя")],  # Новая кнопка
                [KeyboardButton(text="📋 Мои поездки"), KeyboardButton(text="⚙️ Настройки")],
                [KeyboardButton(text="ℹ️ Помощь")]
            ]
        else:  # pl
            buttons = [
                [KeyboardButton(text="🚖 Zamów taxi")],
                [KeyboardButton(text="🍷 Dostawa alkoholu")],  # Новая кнопка
                [KeyboardButton(text="📋 Moje przejazdy"), KeyboardButton(text="⚙️ Ustawienia")],
                [KeyboardButton(text="ℹ️ Pomoc")]
            ]

    elif role == UserRole.DRIVER:
        if language == "en":
            buttons = [
                [KeyboardButton(text="🟢 Go Online"), KeyboardButton(text="🔴 Go Offline")],
                [KeyboardButton(text="📋 My Orders"), KeyboardButton(text="📊 Statistics")],
                [KeyboardButton(text="🚗 My Vehicle"), KeyboardButton(text="⚙️ Settings")]
            ]
        elif language == "ru":
            buttons = [
                [KeyboardButton(text="🟢 В сети"), KeyboardButton(text="🔴 Не в сети")],
                [KeyboardButton(text="📋 Мои заказы"), KeyboardButton(text="📊 Статистика")],
                [KeyboardButton(text="🚗 Мой автомобиль"), KeyboardButton(text="⚙️ Настройки")]
            ]
        else:  # pl
            buttons = [
                [KeyboardButton(text="🟢 Online"), KeyboardButton(text="🔴 Offline")],
                [KeyboardButton(text="📋 Moje zamówienia"), KeyboardButton(text="📊 Statystyki")],
                [KeyboardButton(text="🚗 Mój pojazd"), KeyboardButton(text="⚙️ Ustawienia")]
            ]

    else:  # admin
        buttons = [
            [KeyboardButton(text="👥 Users"), KeyboardButton(text="🚗 Drivers")],
            [KeyboardButton(text="📊 Statistics"), KeyboardButton(text="⚙️ Settings")]
        ]

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_location_keyboard(language: str = "pl") -> ReplyKeyboardMarkup:
    """Клавиатура для отправки локации"""

    if language == "en":
        buttons = [
            [KeyboardButton(text="📍 Send My Location", request_location=True)],
            [KeyboardButton(text="✍️ Enter Address Manually")],
            [KeyboardButton(text="❌ Cancel")]
        ]
    elif language == "ru":
        buttons = [
            [KeyboardButton(text="📍 Отправить мою локацию", request_location=True)],
            [KeyboardButton(text="✍️ Ввести адрес вручную")],
            [KeyboardButton(text="❌ Отмена")]
        ]
    else:  # pl
        buttons = [
            [KeyboardButton(text="📍 Wyślij moją lokalizację", request_location=True)],
            [KeyboardButton(text="✍️ Wpisz adres ręcznie")],
            [KeyboardButton(text="❌ Anuluj")]
        ]

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def get_passengers_keyboard(language: str = "pl") -> ReplyKeyboardMarkup:
    """Клавиатура для выбора количества пассажиров"""

    buttons = [
        [KeyboardButton(text="1"), KeyboardButton(text="2")],
        [KeyboardButton(text="3"), KeyboardButton(text="4")],
    ]

    if language == "en":
        buttons.append([KeyboardButton(text="❌ Cancel")])
    elif language == "ru":
        buttons.append([KeyboardButton(text="❌ Отмена")])
    else:  # pl
        buttons.append([KeyboardButton(text="❌ Anuluj")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def get_ride_confirmation_keyboard(language: str = "pl") -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения поездки"""

    if language == "en":
        buttons = [
            [InlineKeyboardButton(text="✅ Confirm Order", callback_data="confirm_ride")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_ride")]
        ]
    elif language == "ru":
        buttons = [
            [InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm_ride")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_ride")]
        ]
    else:  # pl
        buttons = [
            [InlineKeyboardButton(text="✅ Potwierdź zamówienie", callback_data="confirm_ride")],
            [InlineKeyboardButton(text="❌ Anuluj", callback_data="cancel_ride")]
        ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора языка"""

    buttons = [
        [InlineKeyboardButton(text="🇵🇱 Polski", callback_data="lang_pl")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Алиас для обратной совместимости
def language_keyboard() -> InlineKeyboardMarkup:
    """Алиас для обратной совместимости"""
    return get_language_keyboard()


def get_driver_order_keyboard(language: str = "pl") -> InlineKeyboardMarkup:
    """Клавиатура для водителя при получении заказа"""

    if language == "en":
        buttons = [
            [InlineKeyboardButton(text="✅ Accept Order", callback_data="accept_order")],
            [InlineKeyboardButton(text="❌ Decline", callback_data="decline_order")]
        ]
    elif language == "ru":
        buttons = [
            [InlineKeyboardButton(text="✅ Принять заказ", callback_data="accept_order")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data="decline_order")]
        ]
    else:  # pl
        buttons = [
            [InlineKeyboardButton(text="✅ Przyjmij zamówienie", callback_data="accept_order")],
            [InlineKeyboardButton(text="❌ Odrzuć", callback_data="decline_order")]
        ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_driver_status_keyboard(language: str = "pl", is_online: bool = False) -> ReplyKeyboardMarkup:
    """Клавиатура для управления статусом водителя"""

    if language == "en":
        if is_online:
            buttons = [
                [KeyboardButton(text="🔴 Go Offline")],
                [KeyboardButton(text="📋 Current Orders")],
                [KeyboardButton(text="📊 Today's Stats")]
            ]
        else:
            buttons = [
                [KeyboardButton(text="🟢 Go Online")],
                [KeyboardButton(text="📋 Order History")],
                [KeyboardButton(text="⚙️ Settings")]
            ]
    elif language == "ru":
        if is_online:
            buttons = [
                [KeyboardButton(text="🔴 Уйти в офлайн")],
                [KeyboardButton(text="📋 Текущие заказы")],
                [KeyboardButton(text="📊 Статистика дня")]
            ]
        else:
            buttons = [
                [KeyboardButton(text="🟢 Выйти в онлайн")],
                [KeyboardButton(text="📋 История заказов")],
                [KeyboardButton(text="⚙️ Настройки")]
            ]
    else:  # pl
        if is_online:
            buttons = [
                [KeyboardButton(text="🔴 Przejdź offline")],
                [KeyboardButton(text="📋 Bieżące zamówienia")],
                [KeyboardButton(text="📊 Dzisiejsze statystyki")]
            ]
        else:
            buttons = [
                [KeyboardButton(text="🟢 Przejdź online")],
                [KeyboardButton(text="📋 Historia zamówień")],
                [KeyboardButton(text="⚙️ Ustawienia")]
            ]

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)