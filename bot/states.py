from aiogram.fsm.state import State, StatesGroup


class PetCreation(StatesGroup):
    waiting_species       = State()
    waiting_breed         = State()
    waiting_name          = State()
    waiting_age_unit      = State()
    waiting_age           = State()
    waiting_weight        = State()
    waiting_neutered      = State()
    waiting_activity      = State()
    waiting_food_category = State()
    waiting_confirm       = State()
