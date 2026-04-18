import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.states import PetCreation
from bot.keyboards import breed_keyboard, age_unit_keyboard, confirm_keyboard, main_menu_keyboard, species_keyboard
from app.config import settings

router = Router()

SPECIES_LABELS = {
    "cat": "Кошка", "dog": "Собака", "rodent": "Грызун",
    "bird": "Птица", "reptile": "Рептилия"
}


# SCR-02: выбор вида
@router.callback_query(PetCreation.waiting_species, F.data.startswith("species:"))
async def process_species(callback: CallbackQuery, state: FSMContext):
    species = callback.data.split(":")[1]
    await state.update_data(species=species)
    await state.set_state(PetCreation.waiting_breed)
    await callback.message.edit_text(
        "Шаг 2 из 5\nКакая порода?\n\nНапиши породу или нажми кнопку:",
        reply_markup=breed_keyboard()
    )


# SCR-03: ввод породы текстом
@router.message(PetCreation.waiting_breed)
async def process_breed_text(message: Message, state: FSMContext):
    await state.update_data(breed=message.text.strip())
    await state.set_state(PetCreation.waiting_name)
    await message.answer("Шаг 3 из 5\nКак зовут питомца?")


# SCR-03: метис / не знаю
@router.callback_query(PetCreation.waiting_breed, F.data == "breed:unknown")
async def process_breed_unknown(callback: CallbackQuery, state: FSMContext):
    await state.update_data(breed=None)
    await state.set_state(PetCreation.waiting_name)
    await callback.message.edit_text("Шаг 3 из 5\nКак зовут питомца?")


# SCR-04: ввод имени
@router.message(PetCreation.waiting_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(PetCreation.waiting_age_unit)
    await message.answer(
        "Шаг 4 из 5\nСколько питомцу?",
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
    await message.answer("Шаг 5 из 5\nСколько весит питомец?\n\nВведи вес в кг. Например: 5.2")


# SCR-06: ввод веса
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
    breed_label = data.get("breed") or "Метис"
    summary = (
        f"Проверь данные питомца\n\n"
        f"<b>{data['name']}</b>\n"
        f"Вид:     {SPECIES_LABELS.get(data['species'], data['species'])}\n"
        f"Порода:  {breed_label}\n"
        f"Возраст: {data.get('age_display', str(data['age_months']) + ' мес')}\n"
        f"Вес:     {weight} кг"
    )
    await state.set_state(PetCreation.waiting_confirm)
    await message.answer(summary, parse_mode="HTML", reply_markup=confirm_keyboard())


# SCR-07: подтверждение — сохранить
@router.callback_query(PetCreation.waiting_confirm, F.data == "confirm:save")
async def confirm_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    telegram_id = callback.from_user.id
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/pets",
            json={
                "name": data["name"], "species": data["species"],
                "breed": data.get("breed"), "age_months": data["age_months"],
                "weight_kg": data["weight_kg"], "goal": "maintain"
            },
            headers={"X-Telegram-Id": str(telegram_id)}
        )
    await state.clear()
    if resp.status_code == 201:
        await callback.message.edit_text(
            f"Профиль создан! Теперь я знаю как кормить <b>{data['name']}</b>.\n\n"
            "Выбери что хочешь сделать:",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )
    else:
        await callback.message.edit_text("Что-то пошло не так. Попробуй ещё раз /start")


# SCR-07: подтверждение — изменить
@router.callback_query(PetCreation.waiting_confirm, F.data == "confirm:edit")
async def confirm_edit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_species)
    await callback.message.edit_text(
        "Шаг 1 из 5\nКто твой питомец?",
        reply_markup=species_keyboard()
    )
