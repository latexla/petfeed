import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.keyboards import main_menu_keyboard, pets_keyboard
from app.config import settings

router = Router()


class AiQuestion(StatesGroup):
    waiting_question = State()


async def _get_pets(telegram_id: int) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/pets",
            headers={"X-Telegram-Id": str(telegram_id)}
        )
        return resp.json() if resp.status_code == 200 else []


@router.callback_query(F.data == "menu:ai")
async def start_ai(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    pets = await _get_pets(telegram_id)

    pet_id = None
    if pets:
        data = await state.get_data()
        active_id = data.get("active_pet_id")
        pet = next((p for p in pets if p["id"] == active_id), pets[0])
        pet_id = pet["id"]
        await state.update_data(ai_pet_id=pet_id)
        context_line = f"Питомец: <b>{pet['name']}</b> ({pet['species']})\n\n"
    else:
        context_line = ""

    await state.set_state(AiQuestion.waiting_question)
    await callback.message.edit_text(
        f"{context_line}"
        "Задай любой вопрос о питании или здоровье питомца:\n\n"
        "<i>Например: можно ли кошке давать сырую рыбу? сколько раз кормить щенка?</i>",
        parse_mode="HTML"
    )


@router.message(AiQuestion.waiting_question)
async def handle_question(message: Message, state: FSMContext):
    question = message.text.strip()
    if len(question) < 5:
        await message.answer("Вопрос слишком короткий. Опиши подробнее.")
        return

    data = await state.get_data()
    pet_id = data.get("ai_pet_id")
    telegram_id = message.from_user.id

    await message.answer("Думаю...")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/ai/ask",
            json={"question": question, "pet_id": pet_id},
            headers={"X-Telegram-Id": str(telegram_id)}
        )

    await state.clear()

    if resp.status_code == 429:
        await message.answer(
            "Лимит запросов исчерпан (10/день).\nЗавтра снова доступно.",
            reply_markup=main_menu_keyboard()
        )
        return

    if resp.status_code != 200:
        await message.answer("Сервис временно недоступен. Попробуй позже.", reply_markup=main_menu_keyboard())
        return

    data = resp.json()
    suffix = " (из кэша)" if data["cache_hit"] else f"\n\n<i>Осталось запросов сегодня: {data['requests_left']}</i>"
    await message.answer(
        f"{data['answer']}{suffix}",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )
