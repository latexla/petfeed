import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.keyboards import (
    feedback_rating_keyboard, feedback_feature_keyboard,
    feedback_comment_keyboard, main_menu_keyboard,
)
from bot.states import FeedbackFlow
from app.config import settings

router = Router()


@router.callback_query(F.data == "menu:feedback")
async def start_feedback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FeedbackFlow.waiting_rating)
    await callback.message.edit_text(
        "💬 <b>Обратная связь</b>\n\nКак оцениваешь PetFeed?",
        parse_mode="HTML",
        reply_markup=feedback_rating_keyboard(),
    )


@router.callback_query(F.data == "feedback_start")
async def start_feedback_auto(callback: CallbackQuery, state: FSMContext):
    await state.update_data(fb_source="auto_7d")
    await state.set_state(FeedbackFlow.waiting_rating)
    await callback.message.answer(
        "💬 <b>Оставь отзыв</b>\n\nКак оцениваешь PetFeed?",
        parse_mode="HTML",
        reply_markup=feedback_rating_keyboard(),
    )


@router.callback_query(F.data.startswith("fb_rating:"), FeedbackFlow.waiting_rating)
async def handle_rating(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split(":")[1])
    await state.update_data(fb_rating=rating)
    await state.set_state(FeedbackFlow.waiting_feature)
    await callback.message.edit_text(
        f"Оценка: {'⭐' * rating}\n\n<b>Какую функцию используешь чаще всего?</b>",
        parse_mode="HTML",
        reply_markup=feedback_feature_keyboard(),
    )


@router.callback_query(F.data.startswith("fb_feature:"), FeedbackFlow.waiting_feature)
async def handle_feature(callback: CallbackQuery, state: FSMContext):
    feature = callback.data.split(":", 1)[1]
    await state.update_data(fb_feature=feature)
    await state.set_state(FeedbackFlow.waiting_comment)
    await callback.message.edit_text(
        "Отлично! 👍\n\n<b>Что хочешь улучшить или добавить?</b>\n\n"
        "Напиши свободным текстом или нажми «Пропустить».",
        parse_mode="HTML",
        reply_markup=feedback_comment_keyboard(),
    )


@router.message(FeedbackFlow.waiting_comment)
async def handle_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    await _submit(
        telegram_id=message.from_user.id,
        data=data,
        comment=message.text.strip(),
        reply_fn=message.answer,
        pet_name=data.get("active_pet_name", ""),
    )
    await state.clear()


@router.callback_query(F.data == "fb_skip_comment", FeedbackFlow.waiting_comment)
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await _submit(
        telegram_id=callback.from_user.id,
        data=data,
        comment=None,
        reply_fn=lambda text, **kw: callback.message.edit_text(text, **kw),
        pet_name=data.get("active_pet_name", ""),
    )
    await state.clear()


async def _submit(telegram_id: int, data: dict, comment: str | None, reply_fn, pet_name: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/feedback",
            json={
                "rating": data.get("fb_rating", 3),
                "top_feature": data.get("fb_feature", ""),
                "comment": comment,
                "source": data.get("fb_source", "manual"),
            },
            headers={"X-Telegram-Id": str(telegram_id)},
        )

    if resp.status_code == 409:
        text = "Ты уже оставлял отзыв, спасибо! Если хочешь добавить — напиши в поддержку."
    elif resp.status_code == 201:
        text = "Спасибо! Твой отзыв помогает нам стать лучше 🙏"
    else:
        text = "Что-то пошло не так. Попробуй позже."

    await reply_fn(text, reply_markup=main_menu_keyboard(pet_name))
