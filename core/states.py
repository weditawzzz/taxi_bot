from aiogram.fsm.state import StatesGroup, State

class OrderState(StatesGroup):
    waiting_origin = State()
    waiting_destination = State()
    waiting_payment = State()
    confirmation = State()

class AlcoholOrderState(StatesGroup):
    waiting_products = State()  # Список алкоголя
    waiting_age = State()      # Подтверждение возраста
    waiting_address = State()  # Адрес доставки
    confirmation = State()     # Подтверждение заказа