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


# ===================================================================
# НОВЫЕ КЛАВИАТУРЫ ДЛЯ ПОЛНОГО УПРАВЛЕНИЯ ПОЕЗДКОЙ
# ===================================================================

def get_client_ride_keyboard(language: str = "pl", status: str = "pending") -> InlineKeyboardMarkup:
    """Клавиатура для управления поездкой клиентом"""
    buttons = []

    if status == "pending":
        # Заказ ожидает принятия
        if language == "en":
            buttons = [
                [InlineKeyboardButton(text="❌ Cancel Order", callback_data="cancel_ride")],
                [InlineKeyboardButton(text="📞 Call Support", callback_data="call_support")]
            ]
        elif language == "ru":
            buttons = [
                [InlineKeyboardButton(text="❌ Отменить заказ", callback_data="cancel_ride")],
                [InlineKeyboardButton(text="📞 Связаться с поддержкой", callback_data="call_support")]
            ]
        else:  # pl
            buttons = [
                [InlineKeyboardButton(text="❌ Anuluj zamówienie", callback_data="cancel_ride")],
                [InlineKeyboardButton(text="📞 Skontaktuj się z pomocą", callback_data="call_support")]
            ]

    elif status == "accepted":
        # Водитель принял заказ, едет к пассажиру
        if language == "en":
            buttons = [
                [InlineKeyboardButton(text="📍 Driver Location", callback_data="show_driver_location")],
                [InlineKeyboardButton(text="📞 Call Driver", callback_data="call_driver")],
                [InlineKeyboardButton(text="❌ Cancel Order", callback_data="cancel_ride")]
            ]
        elif language == "ru":
            buttons = [
                [InlineKeyboardButton(text="📍 Местоположение водителя", callback_data="show_driver_location")],
                [InlineKeyboardButton(text="📞 Позвонить водителю", callback_data="call_driver")],
                [InlineKeyboardButton(text="❌ Отменить заказ", callback_data="cancel_ride")]
            ]
        else:  # pl
            buttons = [
                [InlineKeyboardButton(text="📍 Lokalizacja kierowcy", callback_data="show_driver_location")],
                [InlineKeyboardButton(text="📞 Zadzwoń do kierowcy", callback_data="call_driver")],
                [InlineKeyboardButton(text="❌ Anuluj zamówienie", callback_data="cancel_ride")]
            ]

    elif status == "in_progress":
        # Поездка началась
        if language == "en":
            buttons = [
                [InlineKeyboardButton(text="📍 Current Location", callback_data="show_current_location")],
                [InlineKeyboardButton(text="🛑 Request Stop", callback_data="request_stop")],
                [InlineKeyboardButton(text="📞 Call Driver", callback_data="call_driver")]
            ]
        elif language == "ru":
            buttons = [
                [InlineKeyboardButton(text="📍 Текущее местоположение", callback_data="show_current_location")],
                [InlineKeyboardButton(text="🛑 Запросить остановку", callback_data="request_stop")],
                [InlineKeyboardButton(text="📞 Позвонить водителю", callback_data="call_driver")]
            ]
        else:  # pl
            buttons = [
                [InlineKeyboardButton(text="📍 Aktualna lokalizacja", callback_data="show_current_location")],
                [InlineKeyboardButton(text="🛑 Poproś o zatrzymanie", callback_data="request_stop")],
                [InlineKeyboardButton(text="📞 Zadzwoń do kierowcy", callback_data="call_driver")]
            ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_driver_ride_keyboard(language: str = "pl", status: str = "accepted") -> InlineKeyboardMarkup:
    """Клавиатура для управления поездкой водителем"""
    buttons = []

    if status == "accepted":
        # Заказ принят, едем к пассажиру
        if language == "en":
            buttons = [
                [InlineKeyboardButton(text="🧭 Navigate to Pickup", callback_data="navigate_pickup")],
                [InlineKeyboardButton(text="📞 Call Passenger", callback_data="call_passenger")],
                [InlineKeyboardButton(text="✅ I've Arrived", callback_data="driver_arrived")]
            ]
        elif language == "ru":
            buttons = [
                [InlineKeyboardButton(text="🧭 Навигация к пассажиру", callback_data="navigate_pickup")],
                [InlineKeyboardButton(text="📞 Позвонить пассажиру", callback_data="call_passenger")],
                [InlineKeyboardButton(text="✅ Я прибыл", callback_data="driver_arrived")]
            ]
        else:  # pl
            buttons = [
                [InlineKeyboardButton(text="🧭 Nawigacja do pasażera", callback_data="navigate_pickup")],
                [InlineKeyboardButton(text="📞 Zadzwoń do pasażera", callback_data="call_passenger")],
                [InlineKeyboardButton(text="✅ Przyjechałem", callback_data="driver_arrived")]
            ]

    elif status == "arrived":
        # Водитель прибыл к пассажиру
        if language == "en":
            buttons = [
                [InlineKeyboardButton(text="🚦 Start Trip", callback_data="start_trip")],
                [InlineKeyboardButton(text="📞 Call Passenger", callback_data="call_passenger")],
                [InlineKeyboardButton(text="❌ Cancel Order", callback_data="driver_cancel")]
            ]
        elif language == "ru":
            buttons = [
                [InlineKeyboardButton(text="🚦 Начать поездку", callback_data="start_trip")],
                [InlineKeyboardButton(text="📞 Позвонить пассажиру", callback_data="call_passenger")],
                [InlineKeyboardButton(text="❌ Отменить заказ", callback_data="driver_cancel")]
            ]
        else:  # pl
            buttons = [
                [InlineKeyboardButton(text="🚦 Rozpocznij podróż", callback_data="start_trip")],
                [InlineKeyboardButton(text="📞 Zadzwoń do pasażera", callback_data="call_passenger")],
                [InlineKeyboardButton(text="❌ Anuluj zamówienie", callback_data="driver_cancel")]
            ]

    elif status == "in_progress":
        # Поездка в процессе
        if language == "en":
            buttons = [
                [InlineKeyboardButton(text="🧭 Navigate to Destination", callback_data="navigate_destination")],
                [InlineKeyboardButton(text="🛑 Emergency Stop", callback_data="emergency_stop")],
                [InlineKeyboardButton(text="🏁 Complete Trip", callback_data="complete_trip")]
            ]
        elif language == "ru":
            buttons = [
                [InlineKeyboardButton(text="🧭 Навигация к месту назначения", callback_data="navigate_destination")],
                [InlineKeyboardButton(text="🛑 Экстренная остановка", callback_data="emergency_stop")],
                [InlineKeyboardButton(text="🏁 Завершить поездку", callback_data="complete_trip")]
            ]
        else:  # pl
            buttons = [
                [InlineKeyboardButton(text="🧭 Nawigacja do celu", callback_data="navigate_destination")],
                [InlineKeyboardButton(text="🛑 Nagłe zatrzymanie", callback_data="emergency_stop")],
                [InlineKeyboardButton(text="🏁 Zakończ podróż", callback_data="complete_trip")]
            ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_location_sharing_keyboard(language: str = "pl") -> ReplyKeyboardMarkup:
    """Клавиатура для постоянной передачи геопозиции"""
    if language == "en":
        buttons = [
            [KeyboardButton(text="📍 Share Live Location", request_location=True)],
            [KeyboardButton(text="🛑 Stop Sharing Location")]
        ]
    elif language == "ru":
        buttons = [
            [KeyboardButton(text="📍 Транслировать геопозицию", request_location=True)],
            [KeyboardButton(text="🛑 Остановить трансляцию")]
        ]
    else:  # pl
        buttons = [
            [KeyboardButton(text="📍 Udostępnij lokalizację na żywo", request_location=True)],
            [KeyboardButton(text="🛑 Przestań udostępniać lokalizację")]
        ]

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_waiting_keyboard(language: str = "pl") -> InlineKeyboardMarkup:
    """Клавиатура для управления ожиданием"""
    if language == "en":
        buttons = [
            [InlineKeyboardButton(text="⏸️ Stop Waiting", callback_data="stop_waiting")],
            [InlineKeyboardButton(text="📊 Check Wait Time", callback_data="check_wait_time")],
            [InlineKeyboardButton(text="🚦 Continue Trip", callback_data="continue_trip")]
        ]
    elif language == "ru":
        buttons = [
            [InlineKeyboardButton(text="⏸️ Прекратить ожидание", callback_data="stop_waiting")],
            [InlineKeyboardButton(text="📊 Проверить время", callback_data="check_wait_time")],
            [InlineKeyboardButton(text="🚦 Продолжить поездку", callback_data="continue_trip")]
        ]
    else:  # pl
        buttons = [
            [InlineKeyboardButton(text="⏸️ Zakończ oczekiwanie", callback_data="stop_waiting")],
            [InlineKeyboardButton(text="📊 Sprawdź czas", callback_data="check_wait_time")],
            [InlineKeyboardButton(text="🚦 Kontynuuj podróż", callback_data="continue_trip")]
        ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_passenger_waiting_keyboard(language: str = "pl") -> InlineKeyboardMarkup:
    """Клавиатура для пассажира во время ожидания"""
    if language == "en":
        buttons = [
            [InlineKeyboardButton(text="✅ Ready to Continue", callback_data="passenger_ready")],
            [InlineKeyboardButton(text="⏰ I Need More Time", callback_data="need_more_time")],
            [InlineKeyboardButton(text="📞 Call Driver", callback_data="call_driver")]
        ]
    elif language == "ru":
        buttons = [
            [InlineKeyboardButton(text="✅ Готов продолжить", callback_data="passenger_ready")],
            [InlineKeyboardButton(text="⏰ Нужно больше времени", callback_data="need_more_time")],
            [InlineKeyboardButton(text="📞 Позвонить водителю", callback_data="call_driver")]
        ]
    else:  # pl
        buttons = [
            [InlineKeyboardButton(text="✅ Gotowy do kontynuacji", callback_data="passenger_ready")],
            [InlineKeyboardButton(text="⏰ Potrzebuję więcej czasu", callback_data="need_more_time")],
            [InlineKeyboardButton(text="📞 Zadzwoń do kierowcy", callback_data="call_driver")]
        ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)