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
        ]
    ])


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Сохранить", callback_data="confirm:save"),
            InlineKeyboardButton(text="Изменить",  callback_data="confirm:edit"),
        ]
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
        ]
    ])


def activity_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Низкий", callback_data="activity:low"),
         InlineKeyboardButton(text="Умеренный", callback_data="activity:moderate")],
        [InlineKeyboardButton(text="Высокий", callback_data="activity:high"),
         InlineKeyboardButton(text="Рабочий", callback_data="activity:working")],
    ])


def food_category_keyboard(categories: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"{c['name']} (~{int(c['kcal_per_100g'])} ккал/100г)",
            callback_data=f"food_cat:{c['id']}"
        )]
        for c in categories
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
