import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.keyboards import main_menu_keyboard, pets_keyboard
from app.config import settings

router = Router()


class WeightUpdate(StatesGroup):
    waiting_weight = State()


async def _get_pets(telegram_id: int) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/pets",
            headers={"X-Telegram-Id": str(telegram_id)}
        )
        return resp.json() if resp.status_code == 200 else []


@router.callback_query(F.data == "menu:weight")
async def start_weight_update(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    pets = await _get_pets(telegram_id)
    if not pets:
        await callback.message.edit_text("Сначала создай профиль питомца — отправь /start")
        return

    if len(pets) == 1:
        pet = pets[0]
    else:
        data = await state.get_data()
        active_id = data.get("active_pet_id")
        pet = next((p for p in pets if p["id"] == active_id), None)
        if not pet:
            await callback.message.edit_text(
                "Выбери питомца:", reply_markup=pets_keyboard(pets, action="weight")
            )
            return

    await state.update_data(weight_pet_id=pet["id"])
    await state.set_state(WeightUpdate.waiting_weight)
    await callback.message.edit_text(
        f"Текущий вес <b>{pet['name']}</b>: {pet['weight_kg']} кг\n\n"
        "Введи новый вес в кг. Например: 5.8",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("select_pet:weight:"))
async def select_pet_weight(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[2])
    telegram_id = callback.from_user.id
    pets = await _get_pets(telegram_id)
    pet = next((p for p in pets if p["id"] == pet_id), None)
    if not pet:
        return
    await state.update_data(active_pet_id=pet_id, weight_pet_id=pet_id)
    await state.set_state(WeightUpdate.waiting_weight)
    await callback.message.edit_text(
        f"Текущий вес <b>{pet['name']}</b>: {pet['weight_kg']} кг\n\n"
        "Введи новый вес в кг. Например: 5.8",
        parse_mode="HTML"
    )


@router.message(WeightUpdate.waiting_weight)
async def save_weight(message: Message, state: FSMContext):
    try:
        new_weight = float(message.text.strip().replace(",", "."))
        if new_weight <= 0 or new_weight > 1000:
            raise ValueError
    except ValueError:
        await message.answer("Введи корректный вес в кг. Например: 5.8")
        return

    data = await state.get_data()
    pet_id = data.get("weight_pet_id")
    telegram_id = message.from_user.id

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/weight",
            json={"pet_id": pet_id, "weight_kg": new_weight},
            headers={"X-Telegram-Id": str(telegram_id)}
        )

    await state.clear()

    if resp.status_code != 200:
        await message.answer("Не удалось обновить вес. Попробуй позже.", reply_markup=main_menu_keyboard())
        return

    r = resp.json()
    change = r["new_weight"] - r["old_weight"]
    sign = "+" if change >= 0 else ""
    recalc_note = "\n\nРацион пересчитан под новый вес." if r["ration_recalculated"] else ""
    await message.answer(
        f"Вес обновлён: <b>{r['new_weight']} кг</b> ({sign}{change:.1f} кг){recalc_note}",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )
