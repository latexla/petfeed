import httpx
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.states import PetCreation
from bot.keyboards import species_keyboard, main_menu_keyboard, pets_keyboard
from app.config import settings

router = Router()


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

    if len(pets) == 1:
        await state.update_data(active_pet_id=pets[0]["id"])
        await message.answer(
            f"С возвращением! Активный питомец: <b>{pets[0]['name']}</b>\n\nВыбери действие:",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )
    else:
        names = ", ".join(p["name"] for p in pets)
        await message.answer(
            f"С возвращением! Твои питомцы: <b>{names}</b>\n\nВыбери питомца:",
            parse_mode="HTML",
            reply_markup=pets_keyboard(pets, action="main")
        )


@router.callback_query(F.data.startswith("select_pet:main:"))
async def select_active_pet(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[2])
    await state.update_data(active_pet_id=pet_id)
    await callback.message.edit_text("Выбери действие:", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "add_pet")
async def add_pet(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(PetCreation.waiting_species)
    await callback.message.edit_text("Шаг 1 из 5\nКто твой питомец?", reply_markup=species_keyboard())
