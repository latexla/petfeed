import httpx
from io import BytesIO
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.states import PetCreation
from bot.keyboards import (
    breed_method_keyboard, breed_suggestion_keyboard, breed_not_found_keyboard,
    age_unit_keyboard, confirm_keyboard, main_menu_keyboard, species_keyboard,
    neutered_keyboard, activity_keyboard, back_keyboard,
)
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


@router.callback_query(PetCreation.waiting_species, F.data.startswith("species:"))
async def process_species(callback: CallbackQuery, state: FSMContext):
    species = callback.data.split(":")[1]
    await state.update_data(species=species)
    await state.set_state(PetCreation.waiting_breed)
    await callback.message.edit_text(
        "Шаг 2 из 9\nКакая порода?",
        reply_markup=breed_method_keyboard()
    )


@router.callback_query(PetCreation.waiting_breed, F.data == "breed_method:text")
async def breed_choose_text(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_breed_text)
    await callback.message.edit_text("Напиши название породы:", reply_markup=back_keyboard())


@router.callback_query(PetCreation.waiting_breed, F.data == "breed_method:photo")
async def breed_choose_photo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_breed_photo)
    await callback.message.edit_text("Отправь фото питомца 📷", reply_markup=back_keyboard())


@router.callback_query(PetCreation.waiting_breed, F.data == "breed:unknown")
async def process_breed_unknown(callback: CallbackQuery, state: FSMContext):
    await state.update_data(breed=None)
    await state.set_state(PetCreation.waiting_name)
    await callback.message.edit_text("Шаг 3 из 9\nКак зовут питомца?", reply_markup=back_keyboard())


@router.message(PetCreation.waiting_breed_text)
async def process_breed_text_input(message: Message, state: FSMContext):
    data = await state.get_data()
    species = data.get("species", "dog")
    query = message.text.strip()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/breeds",
            params={"species": species, "q": query},
            headers={"X-Telegram-Id": str(message.from_user.id)},
        )

    if resp.status_code != 200:
        await message.answer("Ошибка поиска породы. Попробуй ещё раз.")
        return

    await _handle_breed_result(message, state, resp.json())


@router.message(PetCreation.waiting_breed_photo, F.photo)
async def process_breed_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    species = data.get("species", "dog")

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    buf = BytesIO()
    await message.bot.download_file(file.file_path, destination=buf)
    photo_bytes = buf.getvalue()

    await message.answer("Распознаю породу... ⏳")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/breeds/recognize-photo",
            data={"species": species},
            files={"photo": ("photo.jpg", photo_bytes, "image/jpeg")},
            headers={"X-Telegram-Id": str(message.from_user.id)},
        )

    if resp.status_code != 200:
        await message.answer(
            "Не удалось распознать породу по фото. Попробуй написать название.",
            reply_markup=breed_method_keyboard()
        )
        await state.set_state(PetCreation.waiting_breed)
        return

    await _handle_breed_result(message, state, resp.json())


@router.message(PetCreation.waiting_breed_photo)
async def process_breed_photo_wrong(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, отправь именно фото 📷")


async def _handle_breed_result(message: Message, state: FSMContext, result: dict):
    confidence = result["confidence"]
    candidates = result["candidates"]
    raw_input = result["raw_input"]

    if confidence == "high":
        breed_name = candidates[0]["canonical_name_ru"]
        await state.update_data(breed=breed_name)
        await state.set_state(PetCreation.waiting_name)
        await message.answer("Шаг 3 из 9\nКак зовут питомца?", reply_markup=back_keyboard())

    elif confidence == "medium":
        await state.update_data(
            pending_breed_input=raw_input,
            pending_breed_candidates=candidates
        )
        await state.set_state(PetCreation.waiting_breed_suggest)
        await message.answer(
            "Уточни породу — выбери из вариантов:",
            reply_markup=breed_suggestion_keyboard(candidates)
        )

    else:
        await state.update_data(pending_breed_input=raw_input, pending_breed_candidates=[])
        await state.set_state(PetCreation.waiting_breed_suggest)
        await message.answer(
            f"Порода «{raw_input}» не найдена в реестре. Что сделать?",
            reply_markup=breed_not_found_keyboard()
        )


@router.callback_query(PetCreation.waiting_breed_suggest, F.data.startswith("breed_pick:"))
async def process_breed_pick(callback: CallbackQuery, state: FSMContext):
    breed_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    candidates = data.get("pending_breed_candidates", [])
    match = next((c for c in candidates if c["breed_id"] == breed_id), None)
    breed_name = match["canonical_name_ru"] if match else str(breed_id)
    await state.update_data(breed=breed_name)
    await state.set_state(PetCreation.waiting_name)
    await callback.message.edit_text("Шаг 3 из 9\nКак зовут питомца?", reply_markup=back_keyboard())


@router.callback_query(PetCreation.waiting_breed_suggest, F.data == "breed_raw:save")
async def process_breed_raw_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    raw = data.get("pending_breed_input", "")
    await state.update_data(breed=raw if raw else None)
    await state.set_state(PetCreation.waiting_name)
    await callback.message.edit_text("Шаг 3 из 9\nКак зовут питомца?", reply_markup=back_keyboard())


@router.callback_query(PetCreation.waiting_breed_suggest, F.data == "breed_method:text")
async def process_breed_retry(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_breed_text)
    await callback.message.edit_text("Напиши название породы:", reply_markup=back_keyboard())


@router.message(PetCreation.waiting_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(PetCreation.waiting_age_unit)
    await message.answer(
        "Шаг 4 из 9\nСколько питомцу?",
        reply_markup=age_unit_keyboard()
    )


@router.callback_query(PetCreation.waiting_age_unit, F.data.startswith("age_unit:"))
async def process_age_unit(callback: CallbackQuery, state: FSMContext):
    unit = callback.data.split(":")[1]
    await state.update_data(age_unit=unit)
    await state.set_state(PetCreation.waiting_age)
    if unit == "months":
        await callback.message.edit_text("Введи возраст в месяцах:\n\nНапример: 6, 24, 36", reply_markup=back_keyboard())
    else:
        await callback.message.edit_text("Введи возраст в годах:\n\nНапример: 1, 3, 7", reply_markup=back_keyboard())


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
    await message.answer("Шаг 6 из 9\nСколько весит питомец?\n\nВведи вес в кг. Например: 5.2", reply_markup=back_keyboard())


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
            "Шаг 7 из 9\nПитомец кастрирован / стерилизован?",
            reply_markup=neutered_keyboard()
        )
    else:
        await state.update_data(is_neutered=False)
        await state.set_state(PetCreation.waiting_activity)
        await message.answer(
            "Шаг 7 из 9\nУровень активности питомца?",
            reply_markup=activity_keyboard()
        )


@router.callback_query(PetCreation.waiting_neutered, F.data.startswith("neutered:"))
async def process_neutered(callback: CallbackQuery, state: FSMContext):
    is_neutered = callback.data.split(":")[1] == "yes"
    await state.update_data(is_neutered=is_neutered)
    await state.set_state(PetCreation.waiting_activity)
    await callback.message.edit_text(
        "Шаг 8 из 9\nУровень активности питомца?",
        reply_markup=activity_keyboard()
    )


@router.callback_query(PetCreation.waiting_activity, F.data.startswith("activity:"))
async def process_activity(callback: CallbackQuery, state: FSMContext):
    activity = callback.data.split(":")[1]
    await state.update_data(activity_level=activity)
    data = await state.get_data()

    breed_label = data.get("breed") or "Метис"
    neutered_label = "Да" if data.get("is_neutered") else "Нет"
    activity_label = ACTIVITY_LABELS.get(activity, activity)

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


# ─── BACK HANDLERS ────────────────────────────────────────────────

@router.callback_query(PetCreation.waiting_breed, F.data == "back")
async def back_from_breed(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_species)
    await callback.message.edit_text(
        "Шаг 1 из 9\nКто твой питомец?",
        reply_markup=species_keyboard()
    )


@router.callback_query(PetCreation.waiting_breed_text, F.data == "back")
async def back_from_breed_text(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_breed)
    await callback.message.edit_text(
        "Шаг 2 из 9\nКакая порода?",
        reply_markup=breed_method_keyboard()
    )


@router.callback_query(PetCreation.waiting_breed_photo, F.data == "back")
async def back_from_breed_photo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_breed)
    await callback.message.edit_text(
        "Шаг 2 из 9\nКакая порода?",
        reply_markup=breed_method_keyboard()
    )


@router.callback_query(PetCreation.waiting_breed_suggest, F.data == "back")
async def back_from_breed_suggest(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_breed)
    await callback.message.edit_text(
        "Шаг 2 из 9\nКакая порода?",
        reply_markup=breed_method_keyboard()
    )


@router.callback_query(PetCreation.waiting_name, F.data == "back")
async def back_from_name(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_breed)
    await callback.message.edit_text(
        "Шаг 2 из 9\nКакая порода?",
        reply_markup=breed_method_keyboard()
    )


@router.callback_query(PetCreation.waiting_age_unit, F.data == "back")
async def back_from_age_unit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_name)
    await callback.message.edit_text(
        "Шаг 3 из 9\nКак зовут питомца?",
        reply_markup=back_keyboard()
    )


@router.callback_query(PetCreation.waiting_age, F.data == "back")
async def back_from_age(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_age_unit)
    await callback.message.edit_text(
        "Шаг 4 из 9\nСколько питомцу?",
        reply_markup=age_unit_keyboard()
    )


@router.callback_query(PetCreation.waiting_weight, F.data == "back")
async def back_from_weight(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    unit = data.get("age_unit", "months")
    await state.set_state(PetCreation.waiting_age)
    if unit == "months":
        await callback.message.edit_text(
            "Введи возраст в месяцах:\n\nНапример: 6, 24, 36",
            reply_markup=back_keyboard()
        )
    else:
        await callback.message.edit_text(
            "Введи возраст в годах:\n\nНапример: 1, 3, 7",
            reply_markup=back_keyboard()
        )


@router.callback_query(PetCreation.waiting_neutered, F.data == "back")
async def back_from_neutered(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_weight)
    await callback.message.edit_text(
        "Шаг 6 из 9\nСколько весит питомец?\n\nВведи вес в кг. Например: 5.2",
        reply_markup=back_keyboard()
    )


@router.callback_query(PetCreation.waiting_activity, F.data == "back")
async def back_from_activity(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    age_months = data.get("age_months", 0)
    if age_months >= 12:
        await state.set_state(PetCreation.waiting_neutered)
        await callback.message.edit_text(
            "Шаг 7 из 9\nПитомец кастрирован / стерилизован?",
            reply_markup=neutered_keyboard()
        )
    else:
        await state.set_state(PetCreation.waiting_weight)
        await callback.message.edit_text(
            "Шаг 6 из 9\nСколько весит питомец?\n\nВведи вес в кг. Например: 5.2",
            reply_markup=back_keyboard()
        )


@router.callback_query(PetCreation.waiting_confirm, F.data == "back")
async def back_from_confirm(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_activity)
    await callback.message.edit_text(
        "Шаг 8 из 8\nУровень активности питомца?",
        reply_markup=activity_keyboard()
    )


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


@router.callback_query(PetCreation.waiting_confirm, F.data == "confirm:edit")
async def confirm_edit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_species)
    await callback.message.edit_text(
        "Шаг 1 из 9\nКто твой питомец?",
        reply_markup=species_keyboard()
    )
