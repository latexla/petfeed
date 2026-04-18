import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.keyboards import main_menu_keyboard, pets_keyboard
from app.config import settings

router = Router()


class ReminderSetup(StatesGroup):
    waiting_times = State()


async def _get_pets(telegram_id: int) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/pets",
            headers={"X-Telegram-Id": str(telegram_id)}
        )
        return resp.json() if resp.status_code == 200 else []


async def _show_reminder_prompt(callback: CallbackQuery, state: FSMContext, pet: dict, telegram_id: int):
    async with httpx.AsyncClient() as client:
        rem_resp = await client.get(
            f"{settings.BACKEND_URL}/v1/reminders/{pet['id']}",
            headers={"X-Telegram-Id": str(telegram_id)}
        )
    reminders = rem_resp.json() if rem_resp.status_code == 200 else []
    await state.update_data(pet_id=pet["id"])
    await state.set_state(ReminderSetup.waiting_times)
    if reminders:
        times = ", ".join(r["time_of_day"] for r in reminders)
        text = (
            f"Текущие напоминания для <b>{pet['name']}</b>: {times}\n\n"
            "Введи новое время через запятую:\n"
            "Например: <code>08:00, 20:00</code>"
        )
    else:
        text = (
            f"Напоминания для <b>{pet['name']}</b> не настроены.\n\n"
            "Введи время кормления через запятую:\n"
            "Например: <code>08:00, 20:00</code>"
        )
    await callback.message.edit_text(text, parse_mode="HTML")


@router.callback_query(F.data == "menu:reminders")
async def show_reminders_menu(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    pets = await _get_pets(telegram_id)
    if not pets:
        await callback.message.edit_text("Сначала создай профиль питомца — отправь /start")
        return
    if len(pets) == 1:
        await _show_reminder_prompt(callback, state, pets[0], telegram_id)
    else:
        data = await state.get_data()
        active_id = data.get("active_pet_id")
        pet = next((p for p in pets if p["id"] == active_id), None)
        if pet:
            await _show_reminder_prompt(callback, state, pet, telegram_id)
        else:
            await callback.message.edit_text(
                "Выбери питомца:", reply_markup=pets_keyboard(pets, action="reminders")
            )


@router.callback_query(F.data.startswith("select_pet:reminders:"))
async def select_pet_reminders(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[2])
    telegram_id = callback.from_user.id
    pets = await _get_pets(telegram_id)
    pet = next((p for p in pets if p["id"] == pet_id), None)
    if pet:
        await state.update_data(active_pet_id=pet_id)
        await _show_reminder_prompt(callback, state, pet, telegram_id)


@router.message(ReminderSetup.waiting_times)
async def save_reminders(message: Message, state: FSMContext):
    data = await state.get_data()
    pet_id = data.get("pet_id")
    if not pet_id:
        await message.answer("Что-то пошло не так. Попробуй ещё раз через меню.")
        await state.clear()
        return

    times = [t.strip() for t in message.text.strip().replace(".", ":").split(",")]
    telegram_id = message.from_user.id

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/reminders",
            json={"pet_id": pet_id, "times": times},
            headers={"X-Telegram-Id": str(telegram_id)}
        )

    await state.clear()
    if resp.status_code == 201:
        saved = resp.json()
        times_str = ", ".join(r["time_of_day"] for r in saved)
        await message.answer(
            f"Напоминания установлены: <b>{times_str}</b>\n\nБуду напоминать каждый день!",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )
    else:
        error = resp.json().get("detail", {}).get("error", "Неверный формат")
        await message.answer(
            f"Ошибка: {error}\n\nФормат: <code>08:00, 20:00</code>",
            parse_mode="HTML"
        )
