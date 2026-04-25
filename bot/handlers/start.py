import httpx
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.states import PetCreation
from bot.keyboards import species_keyboard, main_menu_keyboard, pets_keyboard, pet_profile_keyboard
from app.config import settings

router = Router()

SPECIES_LABELS = {
    "cat": "Кошка", "dog": "Собака", "rodent": "Грызун",
    "bird": "Птица", "reptile": "Рептилия"
}

GOAL_LABELS = {
    "maintain": "Поддержание веса", "lose": "Похудение",
    "gain": "Набор веса", "growth": "Рост"
}


async def get_user_pets(telegram_id: int) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/pets",
            headers={"X-Telegram-Id": str(telegram_id)}
        )
        if resp.status_code == 200:
            return resp.json()
    return []


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    telegram_id = message.from_user.id
    pets = await get_user_pets(telegram_id)

    if not pets:
        await message.answer(
            "Добро пожаловать в <b>PetFeed</b>!\n\n"
            "Я помогу правильно кормить твоего питомца — "
            "кошку, собаку, хомяка, черепаху или попугая.\n\n"
            "Давай создадим профиль питомца — это займёт 2 минуты.",
            parse_mode="HTML"
        )
        await state.set_state(PetCreation.waiting_species)
        await message.answer("Шаг 1 из 5\nКто твой питомец?", reply_markup=species_keyboard())
        return

    pet = pets[0]
    await state.update_data(active_pet_id=pet["id"], active_pet_name=pet["name"])

    if len(pets) == 1:
        await message.answer(
            f"С возвращением!\n\nВыбери действие:",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(pet["name"])
        )
    else:
        await message.answer(
            "С возвращением! Выбери питомца:",
            reply_markup=pets_keyboard(pets, action="main")
        )


@router.callback_query(F.data.startswith("select_pet:main:"))
async def select_active_pet(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[2])
    telegram_id = callback.from_user.id
    pets = await get_user_pets(telegram_id)
    pet = next((p for p in pets if p["id"] == pet_id), None)
    if not pet:
        return
    await state.update_data(active_pet_id=pet_id, active_pet_name=pet["name"])
    await callback.message.edit_text(
        "Выбери действие:",
        reply_markup=main_menu_keyboard(pet["name"])
    )


@router.callback_query(F.data == "menu:switch_pet")
async def switch_pet(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    pets = await get_user_pets(telegram_id)
    if len(pets) <= 1:
        await show_pet_profile(callback, state)
        return
    await callback.message.edit_text(
        "Выбери питомца:",
        reply_markup=pets_keyboard(pets, action="main")
    )


@router.callback_query(F.data == "menu:back")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pet_name = data.get("active_pet_name", "")
    await callback.message.edit_text("Выбери действие:", reply_markup=main_menu_keyboard(pet_name))


@router.callback_query(F.data == "menu:pet")
async def show_pet_profile(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    data = await state.get_data()
    active_id = data.get("active_pet_id")
    pets = await get_user_pets(telegram_id)
    if not pets:
        await callback.message.edit_text("Сначала создай профиль питомца — отправь /start")
        return
    pet = next((p for p in pets if p["id"] == active_id), pets[0])
    age_months = pet.get("age_months", 0)
    if age_months >= 12 and age_months % 12 == 0:
        years = age_months // 12
        age_str = f"{years} {'год' if years == 1 else 'года' if 2 <= years <= 4 else 'лет'}"
    else:
        age_str = f"{age_months} мес"
    text = (
        f"Профиль питомца\n\n"
        f"Имя:     <b>{pet['name']}</b>\n"
        f"Вид:     {SPECIES_LABELS.get(pet['species'], pet['species'])}\n"
        f"Порода:  {pet.get('breed') or 'Метис'}\n"
        f"Возраст: {age_str}\n"
        f"Вес:     {pet['weight_kg']} кг\n"
        f"Цель:    {GOAL_LABELS.get(pet.get('goal', 'maintain'), 'Поддержание веса')}"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=pet_profile_keyboard(pet["id"]))


@router.callback_query(F.data.startswith("pet:delete:"))
async def delete_pet(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[2])
    telegram_id = callback.from_user.id
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{settings.BACKEND_URL}/v1/pets/{pet_id}",
            headers={"X-Telegram-Id": str(telegram_id)}
        )
    if resp.status_code == 204:
        await state.clear()
        await callback.message.edit_text(
            "Питомец удалён. Чтобы добавить нового — отправь /start"
        )
    else:
        data = await state.get_data()
        pet_name = data.get("active_pet_name", "")
        await callback.message.edit_text(
            "Не удалось удалить питомца. Попробуй позже.",
            reply_markup=main_menu_keyboard(pet_name)
        )


@router.callback_query(F.data == "add_pet")
async def add_pet(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(PetCreation.waiting_species)
    await callback.message.edit_text("Шаг 1 из 5\nКто твой питомец?", reply_markup=species_keyboard())
