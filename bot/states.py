from aiogram.fsm.state import StatesGroup, State

class OrderStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_username = State()
    waiting_for_delivery = State()
    waiting_for_comment = State()
    confirm = State()
