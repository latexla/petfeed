from aiogram.fsm.state import State, StatesGroup


class PetCreation(StatesGroup):
    waiting_species        = State()
    waiting_breed          = State()   # выбор метода: текст / фото / метис
    waiting_breed_text     = State()   # ввод названия породы
    waiting_breed_photo    = State()   # отправка фото
    waiting_breed_suggest  = State()   # выбор из предложенных вариантов
    waiting_name           = State()
    waiting_age_unit       = State()
    waiting_age            = State()
    waiting_weight         = State()
    waiting_neutered       = State()
    waiting_activity       = State()
    waiting_confirm        = State()
