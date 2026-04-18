import httpx
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.keyboards import main_menu_keyboard, pets_keyboard
from app.config import settings

router = Router()


async def _get_pets(telegram_id: int) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/pets",
            headers={"X-Telegram-Id": str(telegram_id)}
        )
        return resp.json() if resp.status_code == 200 else []


async def _show_ration(callback: CallbackQuery, pet: dict, telegram_id: int):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/nutrition/{pet['id']}",
            headers={"X-Telegram-Id": str(telegram_id)}
        )
    if resp.status_code != 200:
        await callback.message.edit_text("Не удалось рассчитать рацион. Попробуй позже.")
        return
    r = resp.json()
    text = (
        f"Рацион для <b>{pet['name']}</b>\n"
        f"Вес: {pet['weight_kg']} кг\n\n"
        f"Калорий в день:  <b>{r['daily_calories']} ккал</b>\n"
        f"Корма в день:    <b>{r['daily_food_grams']} г</b>\n"
        f"Кормлений:       <b>{r['meals_per_day']} раза в день</b>\n"
        f"Порция за раз:   <b>{r['food_per_meal_grams']} г</b>\n"
    )
    if r["notes"]:
        text += f"\n📌 {r['notes']}"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())


async def _show_stoplist(callback: CallbackQuery, pet: dict, telegram_id: int):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/nutrition/{pet['id']}",
            headers={"X-Telegram-Id": str(telegram_id)}
        )
    if resp.status_code != 200:
        await callback.message.edit_text("Не удалось загрузить стоп-лист. Попробуй позже.")
        return
    r = resp.json()
    stop_foods = r.get("stop_foods", "")
    if stop_foods:
        items = "\n".join(f"• {f.strip()}" for f in stop_foods.split(","))
        text = f"Что нельзя давать <b>{pet['name']}</b>:\n\n{items}"
    else:
        text = f"Стоп-лист для {pet['name']} не найден."
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "menu:nutrition")
async def show_nutrition(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    pets = await _get_pets(telegram_id)
    if not pets:
        await callback.message.edit_text("Сначала создай профиль питомца — отправь /start")
        return
    if len(pets) == 1:
        await _show_ration(callback, pets[0], telegram_id)
    else:
        data = await state.get_data()
        active_id = data.get("active_pet_id")
        pet = next((p for p in pets if p["id"] == active_id), None)
        if pet:
            await _show_ration(callback, pet, telegram_id)
        else:
            await callback.message.edit_text(
                "Выбери питомца:", reply_markup=pets_keyboard(pets, action="nutrition")
            )


@router.callback_query(F.data == "menu:stoplist")
async def show_stoplist(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    pets = await _get_pets(telegram_id)
    if not pets:
        await callback.message.edit_text("Сначала создай профиль питомца — отправь /start")
        return
    if len(pets) == 1:
        await _show_stoplist(callback, pets[0], telegram_id)
    else:
        data = await state.get_data()
        active_id = data.get("active_pet_id")
        pet = next((p for p in pets if p["id"] == active_id), None)
        if pet:
            await _show_stoplist(callback, pet, telegram_id)
        else:
            await callback.message.edit_text(
                "Выбери питомца:", reply_markup=pets_keyboard(pets, action="stoplist")
            )


@router.callback_query(F.data.startswith("select_pet:nutrition:"))
async def select_pet_nutrition(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[2])
    telegram_id = callback.from_user.id
    pets = await _get_pets(telegram_id)
    pet = next((p for p in pets if p["id"] == pet_id), None)
    if pet:
        await state.update_data(active_pet_id=pet_id)
        await _show_ration(callback, pet, telegram_id)


@router.callback_query(F.data.startswith("select_pet:stoplist:"))
async def select_pet_stoplist(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[2])
    telegram_id = callback.from_user.id
    pets = await _get_pets(telegram_id)
    pet = next((p for p in pets if p["id"] == pet_id), None)
    if pet:
        await state.update_data(active_pet_id=pet_id)
        await _show_stoplist(callback, pet, telegram_id)
