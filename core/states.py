from aiogram.fsm.state import StatesGroup, State

class OrderState(StatesGroup):
    waiting_origin = State()
    waiting_destination = State()
    waiting_payment = State()
    confirmation = State()