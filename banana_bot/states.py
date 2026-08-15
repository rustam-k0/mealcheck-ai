from aiogram.fsm.state import State, StatesGroup


class BotStates(StatesGroup):
    language = State()
    settings = State()
    awaiting_food_confirmation = State()
    awaiting_food_correction = State()
    awaiting_diary_confirmation = State()
    awaiting_delete_confirmation = State()
    awaiting_edit_confirmation = State()
