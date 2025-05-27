"""
Состояния для конечных автоматов ботов
"""
from aiogram.fsm.state import State, StatesGroup


class ClientStates(StatesGroup):
    """Состояния для клиентского бота"""

    # Заказ такси
    WAITING_PICKUP_LOCATION = State()
    WAITING_DESTINATION_LOCATION = State()
    WAITING_PASSENGERS_COUNT = State()
    WAITING_RIDE_CONFIRMATION = State()
    WAITING_RIDE_NOTES = State()

    # Управление поездкой
    RIDE_IN_PROGRESS = State()
    WAITING_RATING = State()
    WAITING_REVIEW = State()

    # Настройки
    CHANGING_LANGUAGE = State()
    UPDATING_PROFILE = State()


class DriverStates(StatesGroup):
    """Состояния для водительского бота"""

    # Регистрация водителя
    WAITING_PHONE = State()
    WAITING_VEHICLE_MAKE = State()
    WAITING_VEHICLE_MODEL = State()
    WAITING_VEHICLE_YEAR = State()
    WAITING_VEHICLE_COLOR = State()
    WAITING_VEHICLE_PLATE = State()
    WAITING_DOCUMENTS = State()

    # Работа с заказами
    VIEWING_ORDER = State()
    CONFIRMING_PICKUP = State()
    RIDE_IN_PROGRESS = State()
    CONFIRMING_COMPLETION = State()

    # Управление статусом
    ONLINE = State()
    OFFLINE = State()
    BUSY = State()

    # Настройки
    UPDATING_VEHICLE = State()
    UPDATING_PROFILE = State()


class AdminStates(StatesGroup):
    """Состояния для админских функций"""

    # Управление пользователями
    SEARCHING_USER = State()
    EDITING_USER = State()

    # Управление поездками
    VIEWING_RIDES = State()
    EDITING_RIDE = State()

    # Статистика
    GENERATING_REPORT = State()

    # Настройки системы
    UPDATING_PRICES = State()
    MANAGING_DRIVERS = State()

class OrderState(StatesGroup):
    waiting_origin = State()
    waiting_destination = State()
    waiting_payment = State()
    confirmation = State()

# Упрощенные состояния только для покупки из магазина
class AlcoholOrderState(StatesGroup):
    waiting_products = State()    # Список товаров для покупки
    waiting_budget = State()      # Бюджет на покупки
    waiting_age = State()         # Подтверждение возраста
    waiting_address = State()     # Адрес доставки
    confirmation = State()        # Подтверждение заказа