import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.config import settings
from bot.keyboards import food_picker_filters_keyboard, food_picker_list_keyboard
from bot.states import FoodPicker

router = Router()

DISABLED_MSG = "🔎 Подбор корма сейчас недоступен. Загляни позже!"


async def _fetch_pet(telegram_id: int, pet_id: int) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/pets/{pet_id}",
            headers={"X-Telegram-Id": str(telegram_id)},
        )
    return resp.json() if resp.status_code == 200 else None


async def _fetch_foods(telegram_id: int, params: dict) -> list[dict] | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/commercial-foods",
            params=params,
            headers={"X-Telegram-Id": str(telegram_id)},
        )
    if resp.status_code == 403:
        return None  # feature_food_catalog disabled
    return resp.json() if resp.status_code == 200 else []


@router.callback_query(F.data == "menu:food_picker")
async def open_picker(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pet_id = data.get("active_pet_id") or data.get("meal_pet_id")
    if not pet_id:
        await callback.answer("Сначала выбери питомца", show_alert=True)
        return
    pet = await _fetch_pet(callback.from_user.id, int(pet_id))
    if pet is None:
        await callback.answer("Не удалось загрузить питомца", show_alert=True)
        return
    probe = await _fetch_foods(callback.from_user.id, {"species": pet.get("species", "cat"), "limit": 1})
    if probe is None:
        await callback.answer(DISABLED_MSG, show_alert=True)
        await state.set_state(None)
        return
    await state.update_data(fp_pet_id=int(pet_id), fp_species=pet.get("species", "cat"))
    await state.set_state(FoodPicker.browsing)
    await callback.message.edit_text(
        "🔎 <b>Подбор корма</b>\nВыбери тип корма:",
        parse_mode="HTML",
        reply_markup=food_picker_filters_keyboard(int(pet_id)),
    )


@router.callback_query(FoodPicker.browsing, F.data.startswith("fp_type:"))
async def pick_type(callback: CallbackQuery, state: FSMContext):
    _, food_type, pet_id = callback.data.split(":")
    await _show_list(callback, state, int(pet_id), food_type, offset=0)


@router.callback_query(FoodPicker.browsing, F.data.startswith("fp_page:"))
async def page(callback: CallbackQuery, state: FSMContext):
    _, offset, pet_id = callback.data.split(":")
    data = await state.get_data()
    await _show_list(callback, state, int(pet_id),
                     data.get("fp_type", "all"), offset=int(offset))


async def _show_list(callback, state, pet_id: int, food_type: str, offset: int):
    data = await state.get_data()
    species = data.get("fp_species", "cat")
    await state.update_data(fp_type=food_type)
    params = {"species": species, "limit": 20, "offset": offset}
    if food_type != "all":
        params["food_type"] = food_type
    items = await _fetch_foods(callback.from_user.id, params)
    if items is None:
        await callback.message.edit_text(DISABLED_MSG)
        await state.set_state(None)
        return
    if not items:
        await callback.message.edit_text(
            "Ничего не нашлось 😿",
            reply_markup=food_picker_filters_keyboard(pet_id))
        return
    await callback.message.edit_text(
        f"Найдено кормов: <b>{len(items)}</b>. Выбери, чтобы открыть карточку:",
        parse_mode="HTML",
        reply_markup=food_picker_list_keyboard(items, pet_id, offset),
    )


@router.callback_query(FoodPicker.browsing, F.data.startswith("fp_card:"))
async def show_card(callback: CallbackQuery, state: FSMContext):
    _, food_id, pet_id = callback.data.split(":")
    data = await state.get_data()
    species = data.get("fp_species", "cat")
    items = await _fetch_foods(callback.from_user.id, {"species": species, "limit": 100})
    if items is None:
        await callback.message.edit_text(DISABLED_MSG)
        await state.set_state(None)
        return
    cf = next((i for i in items if i["id"] == int(food_id)), None)
    if cf is None:
        await callback.answer("Корм не найден", show_alert=True)
        return
    tags = ", ".join(cf.get("tags", [])) or "—"
    await callback.message.edit_text(
        f"<b>{cf['brand']} {cf['name']}</b>\n"
        f"Тип: {cf['food_type']} · {cf['life_stage']}\n"
        f"Ккал/100г: {cf['kcal_per_100g']:.0f}\n"
        f"Белок {cf['protein_g']:.0f} / Жир {cf['fat_g']:.0f} / Угл {cf['carb_g']:.0f} г\n"
        f"Назначение: {tags}",
        parse_mode="HTML",
        reply_markup=food_picker_filters_keyboard(int(pet_id)),
    )
