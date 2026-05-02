from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def species_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Кошка",  callback_data="species:cat"),
            InlineKeyboardButton(text="Собака", callback_data="species:dog"),
        ],
        [
            InlineKeyboardButton(text="Грызун",  callback_data="species:rodent"),
            InlineKeyboardButton(text="Птица",   callback_data="species:bird"),
        ],
        [
            InlineKeyboardButton(text="Рептилия", callback_data="species:reptile"),
        ],
    ])


def breed_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Метис / Не знаю", callback_data="breed:unknown")]
    ])


def age_unit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="В месяцах", callback_data="age_unit:months"),
            InlineKeyboardButton(text="В годах",   callback_data="age_unit:years"),
        ],
        [InlineKeyboardButton(text="← Назад", callback_data="back")],
    ])


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Сохранить", callback_data="confirm:save"),
            InlineKeyboardButton(text="Изменить",  callback_data="confirm:edit"),
        ],
        [InlineKeyboardButton(text="← Назад", callback_data="back")],
    ])


def pets_keyboard(pets: list[dict], action: str) -> InlineKeyboardMarkup:
    """Список питомцев для выбора. action: 'nutrition'|'stoplist'|'reminders'|'weight'"""
    rows = [
        [InlineKeyboardButton(
            text=f"{p['name']} ({p['species']})",
            callback_data=f"select_pet:{action}:{p['id']}"
        )]
        for p in pets
    ]
    rows.append([InlineKeyboardButton(text="+ Добавить питомца", callback_data="add_pet")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_keyboard(pet_name: str = "") -> InlineKeyboardMarkup:
    rows = []
    if pet_name:
        rows.append([InlineKeyboardButton(text=f"🐾 {pet_name} ▼", callback_data="menu:switch_pet")])
    rows += [
        [InlineKeyboardButton(text="Рацион питания",       callback_data="menu:nutrition")],
        [InlineKeyboardButton(text="Что нельзя давать",    callback_data="menu:stoplist")],
        [InlineKeyboardButton(text="Напоминания",           callback_data="menu:reminders")],
        [InlineKeyboardButton(text="Обновить вес",          callback_data="menu:weight")],
        [InlineKeyboardButton(text="Заказать корм",         callback_data="menu:order")],
        [InlineKeyboardButton(text="Задать вопрос AI",      callback_data="menu:ai")],
        [InlineKeyboardButton(text="Профиль питомца",       callback_data="menu:pet")],
        [InlineKeyboardButton(text="+ Добавить питомца",    callback_data="add_pet")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pet_profile_keyboard(pet_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить питомца", callback_data=f"pet:delete:{pet_id}")],
        [InlineKeyboardButton(text="Назад",           callback_data="menu:back")],
    ])


def neutered_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data="neutered:yes"),
            InlineKeyboardButton(text="Нет", callback_data="neutered:no"),
        ],
        [InlineKeyboardButton(text="← Назад", callback_data="back")],
    ])


def activity_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Низкий", callback_data="activity:low"),
         InlineKeyboardButton(text="Умеренный", callback_data="activity:moderate")],
        [InlineKeyboardButton(text="Высокий", callback_data="activity:high"),
         InlineKeyboardButton(text="Рабочий", callback_data="activity:working")],
        [InlineKeyboardButton(text="← Назад", callback_data="back")],
    ])


def breed_method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать название", callback_data="breed_method:text")],
        [InlineKeyboardButton(text="Отправить фото 📷", callback_data="breed_method:photo")],
        [InlineKeyboardButton(text="Метис / Не знаю", callback_data="breed:unknown")],
        [InlineKeyboardButton(text="← Назад", callback_data="back")],
    ])


def breed_suggestion_keyboard(candidates: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"{c['canonical_name_ru']} ({c['canonical_name']})",
            callback_data=f"breed_pick:{c['breed_id']}"
        )]
        for c in candidates
    ]
    rows.append([InlineKeyboardButton(
        text="Сохранить как введено", callback_data="breed_raw:save"
    )])
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def breed_not_found_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ввести заново", callback_data="breed_method:text")],
        [InlineKeyboardButton(text="Сохранить как введено", callback_data="breed_raw:save")],
        [InlineKeyboardButton(text="← Назад", callback_data="back")],
    ])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data="back")]
    ])
