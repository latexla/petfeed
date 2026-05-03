import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.states import MealBuilder
from bot.keyboards import (
    meal_type_keyboard, meal_progress_keyboard, meal_l2_keyboard, main_menu_keyboard
)
from app.config import settings

router = Router()

FOOD_TYPE_LABELS = {
    "natural":  "🥩 Натуралка",
    "prepared": "🥫 Корм",
    "mixed":    "🔀 Смешанное",
}
EXAMPLES = {
    "natural":  "курица, говядина, гречка, морковь, яйцо",
    "prepared": "Royal Canin, Purina Pro Plan, Hills",
    "mixed":    "курица + гречка + сухой корм",
}


# ── Entry points ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("meal_start:"))
async def start_meal_builder(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[1])
    await state.update_data(meal_pet_id=pet_id)
    await state.set_state(MealBuilder.waiting_type)
    await callback.message.edit_text(
        "Чем будешь кормить?",
        reply_markup=meal_type_keyboard()
    )


@router.callback_query(F.data == "meal_cancel")
async def cancel_meal(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pet_name = data.get("active_pet_name", "")
    await state.set_state(None)
    await callback.message.edit_text("Главное меню", reply_markup=main_menu_keyboard(pet_name))


# ── Type selection ───────────────────────────────────────────────────

@router.callback_query(MealBuilder.waiting_type, F.data.startswith("meal_type:"))
async def choose_food_type(callback: CallbackQuery, state: FSMContext):
    food_type = callback.data.split(":")[1]
    await state.update_data(meal_food_type=food_type)
    await state.set_state(MealBuilder.waiting_product)
    examples = EXAMPLES.get(food_type, "")
    await callback.message.edit_text(
        f"Тип: <b>{FOOD_TYPE_LABELS[food_type]}</b>\n\n"
        f"Вводи продукты по одному.\n"
        f"Примеры: {examples}\n\n"
        "Что добавим первым?",
        parse_mode="HTML",
    )


# ── Product input ────────────────────────────────────────────────────

@router.message(MealBuilder.waiting_product)
async def handle_product_input(message: Message, state: FSMContext):
    data = await state.get_data()
    pet_id = data.get("meal_pet_id")
    food_type = data.get("meal_food_type", "natural")
    await _add_product(message, state, message.from_user.id,
                       pet_id, food_type, message.text.strip(), force_add=False)


async def _add_product(message_or_cb, state: FSMContext,
                       telegram_id: int, pet_id: int, food_type: str,
                       product_name: str, force_add: bool):
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/meal/add-product",
            json={
                "pet_id": pet_id,
                "product_name": product_name,
                "food_type": food_type,
                "force_add": force_add,
            },
            headers={"X-Telegram-Id": str(telegram_id)},
        )

    if resp.status_code != 200:
        text = "Ошибка сервера. Попробуй ещё раз."
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer(text)
        else:
            await message_or_cb.message.edit_text(text)
        return

    r = resp.json()
    status = r.get("status")

    if status == "blocked":
        text = r["message"]
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer(text, parse_mode="HTML")
        else:
            await message_or_cb.message.edit_text(text, parse_mode="HTML")
        return

    if status == "warning":
        keyboard = meal_l2_keyboard(r["product_name"])
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer(r["message"], parse_mode="HTML", reply_markup=keyboard)
        else:
            await message_or_cb.message.edit_text(r["message"], parse_mode="HTML", reply_markup=keyboard)
        return

    if status == "not_found":
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer(r["message"])
        else:
            await message_or_cb.message.edit_text(r["message"])
        return

    # status == "added"
    item = r["item"]
    progress = r["progress"]
    done = r.get("done", False)
    low_conf = r.get("low_confidence", False)

    conf_note = "\n⚠️ <i>Данные приблизительные — продукт не найден в базе.</i>" if low_conf else ""

    prog_lines = []
    if "kcal_pct" in progress:
        prog_lines.append(f"ккал {int(progress['kcal_pct'])}%")
    if "protein_g_pct" in progress:
        prog_lines.append(f"белок {int(progress['protein_g_pct'])}%")
    if "fat_g_pct" in progress:
        prog_lines.append(f"жир {int(progress['fat_g_pct'])}%")
    prog_str = " · ".join(prog_lines)

    text = (
        f"✅ <b>{item['name']}</b>: {int(item['grams'])}г = {item['kcal']} ккал\n"
        f"📊 {prog_str}{conf_note}"
    )
    if done:
        text += "\n\n<b>Норма закрыта ✅</b>"
    elif r.get("recommendation"):
        text += f"\n💡 {r['recommendation']}"

    keyboard = meal_progress_keyboard(pet_id)
    if isinstance(message_or_cb, Message):
        await message_or_cb.answer(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await message_or_cb.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)


# ── Level 2 confirmation ─────────────────────────────────────────────

@router.callback_query(MealBuilder.waiting_product, F.data.startswith("meal_l2_yes:"))
async def confirm_l2(callback: CallbackQuery, state: FSMContext):
    product_name = callback.data.split(":", 1)[1]
    data = await state.get_data()
    await _add_product(callback, state, callback.from_user.id,
                       data.get("meal_pet_id"), data.get("meal_food_type", "natural"),
                       product_name, force_add=True)


@router.callback_query(MealBuilder.waiting_product, F.data == "meal_l2_no")
async def skip_l2(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Хорошо, введи другой продукт:")


# ── Summary ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("meal_summary:"))
async def show_summary(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[1])
    telegram_id = callback.from_user.id
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/meal/summary/{pet_id}",
            headers={"X-Telegram-Id": str(telegram_id)},
        )
    if resp.status_code != 200:
        await callback.message.edit_text("Не удалось загрузить итог. Попробуй позже.")
        return
    r = resp.json()

    items_text = "\n".join(f"{it['name']} — {int(it['grams'])}г" for it in r["items"])
    sep = "─" * 22
    totals = r["totals"]
    targets = r["targets"]
    required = r.get("required_micros", [])

    def fmt_line(label, key, unit):
        got = totals.get(key, 0)
        tgt = targets.get(key, 0)
        if tgt:
            pct = int(got / tgt * 100)
            icon = "✅" if pct >= 90 else "⚠️"
            return f"{label}: {round(got,1)} / {round(tgt,1)} {unit} ({pct}%) {icon}"
        return f"{label}: {round(got,1)} {unit}"

    lines = [
        "🍽 <b>Порция (1 кормление)</b>\n",
        items_text, sep,
        fmt_line("Энергия", "kcal", "ккал"),
        fmt_line("Белок",   "protein_g", "г"),
        fmt_line("Жир",     "fat_g", "г"),
    ]
    if r.get("ca_p_ratio"):
        ratio = r["ca_p_ratio"]
        icon = "✅" if 1.2 <= ratio <= 1.4 else "⚠️"
        lines.append(f"Ca:P: {ratio}:1 {icon}")
    for micro in required:
        if micro in ("calcium_mg", "phosphorus_mg"):
            continue
        labels = {"omega3_mg": "Омега-3", "taurine_mg": "Таурин"}
        if micro in labels:
            lines.append(fmt_line(labels[micro], micro, "мг"))
    if r.get("tip"):
        lines.append(f"\n💡 {r['tip']}")
    lines.append("\n<i>⚠️ Расчёт приблизительный. Проконсультируйся с ветеринаром.</i>")

    data = await state.get_data()
    pet_name = data.get("active_pet_name", "")
    await state.set_state(None)
    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=main_menu_keyboard(pet_name)
    )


# ── Undo / Reset ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("meal_undo:"))
async def undo_last(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[1])
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/meal/undo-last/{pet_id}",
            headers={"X-Telegram-Id": str(callback.from_user.id)},
        )
    if resp.status_code == 200:
        count = resp.json().get("items_count", 0)
        await callback.answer(f"Последний продукт удалён. Продуктов: {count}")
    else:
        await callback.answer("Нечего отменять.")


@router.callback_query(F.data.startswith("meal_reset:"))
async def reset_meal(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[1])
    async with httpx.AsyncClient() as client:
        await client.delete(
            f"{settings.BACKEND_URL}/v1/meal/reset/{pet_id}",
            headers={"X-Telegram-Id": str(callback.from_user.id)},
        )
    await state.set_state(MealBuilder.waiting_type)
    await callback.message.edit_text(
        "Начнём заново. Чем будешь кормить?",
        reply_markup=meal_type_keyboard()
    )
