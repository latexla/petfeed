import httpx
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
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


async def _show_ration(callback: CallbackQuery, pet: dict, telegram_id: int, pet_name: str = ""):
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
        f"<b>Энергия</b>\n"
        f"Калорий в день:  <b>{r['daily_calories']} ккал</b>\n"
        f"Кормлений:       <b>{r['meals_per_day']} раза в день</b>\n\n"
        f"<b>Нутриенты (минимум)</b>\n"
        f"Белок:  {r['protein_min_g']} г/день\n"
        f"Жир:    {r['fat_min_g']} г/день\n"
        f"Ca:P    оптимум 1.2–1.4:1\n"
    )

    if r.get("hypoglycemia_warning"):
        text += "\n⚠️ Щенок до 4 мес — не пропускай кормления! Риск гипогликемии.\n"

    if r.get("recommendations"):
        text += "\n<b>Рекомендации</b>\n"
        for rec in r["recommendations"]:
            text += f"• {rec}\n"

    text += "\n<i>⚠️ Расчёт — отправная точка. Индивидуальная потребность может отличаться на ±30%.</i>"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍽 Подобрать порцию",
                              callback_data=f"meal_start:{pet['id']}")],
        [InlineKeyboardButton(text="← Главное меню", callback_data="menu:back")],
    ])

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except TelegramBadRequest:
        pass


async def _show_stoplist(callback: CallbackQuery, pet: dict, telegram_id: int, pet_name: str = ""):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/nutrition/{pet['id']}",
            headers={"X-Telegram-Id": str(telegram_id)}
        )
    if resp.status_code != 200:
        await callback.message.edit_text("Не удалось загрузить стоп-лист. Попробуй позже.")
        return
    r = resp.json()

    level1 = r.get("stop_foods_level1", [])
    level2 = r.get("stop_foods_level2", [])
    level3 = r.get("stop_foods_level3", [])

    text = ""

    if level1:
        names = ", ".join(f["product_name"] for f in level1)
        text += f"⛔ <b>Никогда не давать:</b>\n{names}\n\n"

    if level2:
        names = ", ".join(f["product_name"] for f in level2)
        text += f"⚠️ <b>Нежелательно регулярно:</b>\n{names}\n\n"

    if level3:
        text += (
            "ℹ️ <b>Пищевые аллергены</b>\n"
            "Определяются индивидуально через элиминационную диету у ветеринара. "
            "Бот не выдаёт запреты без диагноза."
        )

    if not text:
        text = "Стоп-лист для этого вида не найден."

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard(pet_name))
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "menu:nutrition")
async def show_nutrition(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    data = await state.get_data()
    pet_name = data.get("active_pet_name", "")
    pets = await _get_pets(telegram_id)
    if not pets:
        await callback.message.edit_text("Сначала создай профиль питомца — отправь /start")
        return
    if len(pets) == 1:
        await _show_ration(callback, pets[0], telegram_id, pet_name)
    else:
        active_id = data.get("active_pet_id")
        pet = next((p for p in pets if p["id"] == active_id), None)
        if pet:
            await _show_ration(callback, pet, telegram_id, pet_name)
        else:
            await callback.message.edit_text(
                "Выбери питомца:", reply_markup=pets_keyboard(pets, action="nutrition")
            )


@router.callback_query(F.data == "menu:stoplist")
async def show_stoplist(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    data = await state.get_data()
    pet_name = data.get("active_pet_name", "")
    pets = await _get_pets(telegram_id)
    if not pets:
        await callback.message.edit_text("Сначала создай профиль питомца — отправь /start")
        return
    if len(pets) == 1:
        await _show_stoplist(callback, pets[0], telegram_id, pet_name)
    else:
        active_id = data.get("active_pet_id")
        pet = next((p for p in pets if p["id"] == active_id), None)
        if pet:
            await _show_stoplist(callback, pet, telegram_id, pet_name)
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
        await state.update_data(active_pet_id=pet_id, active_pet_name=pet["name"])
        await _show_ration(callback, pet, telegram_id, pet["name"])


@router.callback_query(F.data.startswith("select_pet:stoplist:"))
async def select_pet_stoplist(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[2])
    telegram_id = callback.from_user.id
    pets = await _get_pets(telegram_id)
    pet = next((p for p in pets if p["id"] == pet_id), None)
    if pet:
        await state.update_data(active_pet_id=pet_id, active_pet_name=pet["name"])
        await _show_stoplist(callback, pet, telegram_id, pet["name"])


@router.callback_query(F.data == "menu:back")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pet_name = data.get("active_pet_name", "")
    await callback.message.edit_text("Главное меню", reply_markup=main_menu_keyboard(pet_name))
