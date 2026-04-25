import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.states import PetCreation
from bot.keyboards import (breed_keyboard, age_unit_keyboard, confirm_keyboard,
                           main_menu_keyboard, species_keyboard,
                           neutered_keyboard, activity_keyboard, food_category_keyboard)
from app.config import settings

router = Router()

SPECIES_LABELS = {
    "cat": "Кошка", "dog": "Собака", "rodent": "Грызун",
    "bird": "Птица", "reptile": "Рептилия"
}

ACTIVITY_LABELS = {
    "low": "Низкий", "moderate": "Умеренный",
    "high": "Высокий", "working": "Рабочий"
}


# SCR-02: выбор вида
@router.callback_query(PetCreation.waiting_species, F.data.startswith("species:"))
async def process_species(callback: CallbackQuery, state: FSMContext):
    species = callback.data.split(":")[1]
    await state.update_data(species=species)
    await state.set_state(PetCreation.waiting_breed)
    await callback.message.edit_text(
        "Шаг 2 из 8\nКакая порода?\n\nНапиши породу или нажми кнопку:",
        reply_markup=breed_keyboard()
    )


# SCR-03: ввод породы текстом
@router.message(PetCreation.waiting_breed)
async def process_breed_text(message: Message, state: FSMContext):
    await state.update_data(breed=message.text.strip())
    await state.set_state(PetCreation.waiting_name)
    await message.answer("Шаг 3 из 8\nКак зовут питомца?")


# SCR-03: метис / не знаю
@router.callback_query(PetCreation.waiting_breed, F.data == "breed:unknown")
async def process_breed_unknown(callback: CallbackQuery, state: FSMContext):
    await state.update_data(breed=None)
    await state.set_state(PetCreation.waiting_name)
    await callback.message.edit_text("Шаг 3 из 8\nКак зовут питомца?")


# SCR-04: ввод имени
@router.message(PetCreation.waiting_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(PetCreation.waiting_age_unit)
    await message.answer(
        "Шаг 4 из 8\nСколько питомцу?",
        reply_markup=age_unit_keyboard()
    )


# SCR-05а: выбор единицы возраста
@router.callback_query(PetCreation.waiting_age_unit, F.data.startswith("age_unit:"))
async def process_age_unit(callback: CallbackQuery, state: FSMContext):
    unit = callback.data.split(":")[1]
    await state.update_data(age_unit=unit)
    await state.set_state(PetCreation.waiting_age)
    if unit == "months":
        await callback.message.edit_text("Введи возраст в месяцах:\n\nНапример: 6, 24, 36")
    else:
        await callback.message.edit_text("Введи возраст в годах:\n\nНапример: 1, 3, 7")


# SCR-05б: ввод числа возраста
@router.message(PetCreation.waiting_age)
async def process_age(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        data = await state.get_data()
        unit_label = "месяцев" if data.get("age_unit") == "months" else "лет"
        await message.answer(f"Введи целое положительное число ({unit_label}). Например: 3")
        return

    value = int(text)
    data = await state.get_data()
    unit = data.get("age_unit", "months")

    if unit == "years":
        age_months = value * 12
        age_display = f"{value} {'год' if value == 1 else 'года' if 2 <= value <= 4 else 'лет'} ({age_months} мес)"
    else:
        age_months = value
        age_display = f"{age_months} мес"

    await state.update_data(age_months=age_months, age_display=age_display)
    await state.set_state(PetCreation.waiting_weight)
    await message.answer("Шаг 5 из 8\nСколько весит питомец?\n\nВведи вес в кг. Например: 5.2")


# SCR-06: ввод веса → кастрация или активность
@router.message(PetCreation.waiting_weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text.strip().replace(",", "."))
        if weight <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи вес в кг. Например: 5.2")
        return
    await state.update_data(weight_kg=weight)
    data = await state.get_data()
    age_months = data.get("age_months", 0)

    if age_months >= 12:
        await state.set_state(PetCreation.waiting_neutered)
        await message.answer(
            "Шаг 6 из 8\nПитомец кастрирован / стерилизован?",
            reply_markup=neutered_keyboard()
        )
    else:
        await state.update_data(is_neutered=False)
        await state.set_state(PetCreation.waiting_activity)
        await message.answer(
            "Шаг 6 из 8\nУровень активности питомца?",
            reply_markup=activity_keyboard()
        )


# SCR-06a: статус кастрации
@router.callback_query(PetCreation.waiting_neutered, F.data.startswith("neutered:"))
async def process_neutered(callback: CallbackQuery, state: FSMContext):
    is_neutered = callback.data.split(":")[1] == "yes"
    await state.update_data(is_neutered=is_neutered)
    await state.set_state(PetCreation.waiting_activity)
    await callback.message.edit_text(
        "Шаг 7 из 8\nУровень активности питомца?",
        reply_markup=activity_keyboard()
    )


# SCR-07: уровень активности
@router.callback_query(PetCreation.waiting_activity, F.data.startswith("activity:"))
async def process_activity(callback: CallbackQuery, state: FSMContext):
    activity = callback.data.split(":")[1]
    await state.update_data(activity_level=activity)
    await state.set_state(PetCreation.waiting_food_category)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/nutrition/food-categories",
            headers={"X-Telegram-Id": str(callback.from_user.id)}
        )
    if resp.status_code == 200:
        categories = resp.json()
    else:
        categories = [
            {"id": 1, "name": "Сухой корм", "kcal_per_100g": 350},
            {"id": 2, "name": "Влажный корм", "kcal_per_100g": 85},
            {"id": 3, "name": "Натуральный", "kcal_per_100g": 150},
            {"id": 4, "name": "BARF (сырое)", "kcal_per_100g": 130},
        ]
    await callback.message.edit_text(
        "Шаг 8 из 8\nЧем кормите питомца?",
        reply_markup=food_category_keyboard(categories)
    )


# SCR-08: тип корма → подтверждение
@router.callback_query(PetCreation.waiting_food_category, F.data.startswith("food_cat:"))
async def process_food_category(callback: CallbackQuery, state: FSMContext):
    food_category_id = int(callback.data.split(":")[1])
    await state.update_data(food_category_id=food_category_id)
    data = await state.get_data()

    breed_label = data.get("breed") or "Метис"
    neutered_label = "Да" if data.get("is_neutered") else "Нет"
    activity_label = ACTIVITY_LABELS.get(data.get("activity_level", "moderate"), "Умеренный")

    summary = (
        f"Проверь данные питомца\n\n"
        f"<b>{data['name']}</b>\n"
        f"Вид:          {SPECIES_LABELS.get(data['species'], data['species'])}\n"
        f"Порода:       {breed_label}\n"
        f"Возраст:      {data.get('age_display', str(data['age_months']) + ' мес')}\n"
        f"Вес:          {data['weight_kg']} кг\n"
        f"Кастрирован:  {neutered_label}\n"
        f"Активность:   {activity_label}"
    )
    await state.set_state(PetCreation.waiting_confirm)
    await callback.message.edit_text(summary, parse_mode="HTML", reply_markup=confirm_keyboard())


# SCR-09: подтверждение — сохранить
@router.callback_query(PetCreation.waiting_confirm, F.data == "confirm:save")
async def confirm_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    telegram_id = callback.from_user.id
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/pets",
            json={
                "name": data["name"],
                "species": data["species"],
                "breed": data.get("breed"),
                "age_months": data["age_months"],
                "weight_kg": data["weight_kg"],
                "goal": "maintain",
                "is_neutered": data.get("is_neutered", False),
                "activity_level": data.get("activity_level", "moderate"),
                "physio_status": data.get("physio_status", "normal"),
                "food_category_id": data.get("food_category_id"),
            },
            headers={"X-Telegram-Id": str(telegram_id)}
        )
    if resp.status_code == 201:
        pet = resp.json()
        await state.set_state(None)
        await state.update_data(active_pet_id=pet["id"], active_pet_name=pet["name"])
        await callback.message.edit_text(
            f"Профиль создан! Теперь я знаю как кормить <b>{data['name']}</b>.\n\n"
            "Выбери что хочешь сделать:",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(data["name"])
        )
    else:
        await state.clear()
        await callback.message.edit_text("Что-то пошло не так. Попробуй ещё раз /start")


# SCR-09: подтверждение — изменить
@router.callback_query(PetCreation.waiting_confirm, F.data == "confirm:edit")
async def confirm_edit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_species)
    await callback.message.edit_text(
        "Шаг 1 из 8\nКто твой питомец?",
        reply_markup=species_keyboard()
    )
