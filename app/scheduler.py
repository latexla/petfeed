import logging
import ssl
from datetime import datetime, date, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, cast, Date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


def _reminder_keyboard(pet_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍽 Что дать?", callback_data=f"meal_start:{pet_id}")]
    ])


async def check_and_send_reminders():
    if _bot is None:
        return
    now = datetime.now().strftime("%H:%M")
    engine = create_async_engine(settings.async_database_url, connect_args={"ssl": _ssl_ctx})
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        from app.repositories.reminder_repo import ReminderRepository
        from app.repositories.pet_repo import PetRepository
        from app.models.user import User

        reminders = await ReminderRepository(session).get_all_active()
        due = [r for r in reminders if r.time_of_day == now]
        for reminder in due:
            pet = await PetRepository(session).get_by_id(
                pet_id=reminder.pet_id, owner_id=reminder.user_id
            )
            user = await session.get(User, reminder.user_id)
            if pet is None or user is None:
                continue
            try:
                await _bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"Время кормить <b>{pet.name}</b>!\n\nНе забудь про правильную порцию.",
                    parse_mode="HTML",
                    reply_markup=_reminder_keyboard(pet.id),
                )
            except Exception as e:
                logger.warning(f"Reminder send failed for user {user.telegram_id}: {e}")
    await engine.dispose()


async def send_feedback_requests():
    if _bot is None:
        return
    from app.models.user import User
    from app.models.user_feedback import UserFeedback

    target_date = date.today() - timedelta(days=7)
    engine = create_async_engine(settings.async_database_url, connect_args={"ssl": _ssl_ctx})
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        already_submitted = select(UserFeedback.user_id)
        stmt = (
            select(User)
            .where(
                cast(User.created_at, Date) == target_date,
                User.is_active.is_(True),
                ~User.id.in_(already_submitted),
            )
        )
        users = (await session.execute(stmt)).scalars().all()

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Оставить отзыв", callback_data="feedback_start")]
        ])

        for user in users:
            try:
                await _bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "Привет! Ты уже неделю с нами 🐾\n\n"
                        "Расскажи, как тебе PetFeed? Займёт 30 секунд "
                        "и поможет нам сделать бота лучше."
                    ),
                    reply_markup=kb,
                )
            except Exception as e:
                logger.warning(f"Feedback request failed for {user.telegram_id}: {e}")

    await engine.dispose()


async def save_daily_sessions():
    """Nightly job: save all Redis daily sessions from yesterday to feeding_sessions DB."""
    yesterday = str(date.today() - timedelta(days=1))

    engine = create_async_engine(settings.async_database_url, connect_args={"ssl": _ssl_ctx})
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db_session:
        from app.repositories.meal_repo import MealRepository
        from app.repositories.pet_repo import PetRepository
        from app.repositories.nutrition_repo import NutritionRepository
        from app.services.pet_service import PetService
        from app.routers.meal import _save_daily_session
        import json as _json

        repo = MealRepository(db_session)
        keys = await repo.scan_daily_keys()

        for key in keys:
            try:
                from app.redis_client import get_redis
                redis = get_redis()
                raw = await redis.get(key)
                if not raw:
                    continue
                data = _json.loads(raw)
                if data.get("date") != yesterday:
                    continue

                parts = key.split(":")
                if len(parts) != 3:
                    continue
                pet_id = int(parts[2])

                pet = await PetService(PetRepository(db_session)).get_by_id_no_owner(pet_id)
                if not pet:
                    continue
                ration = await NutritionRepository(db_session).get_ration_by_pet(pet_id)
                if not ration:
                    continue

                await _save_daily_session(data, pet, ration, db_session)
                await redis.delete(key)
                logger.info("Nightly: saved daily session for pet %s (%s)", pet_id, yesterday)
            except Exception as e:
                logger.error("Nightly: failed to process key %s: %s", key, e)

    await engine.dispose()


def start_scheduler(bot):
    set_bot(bot)
    scheduler.add_job(check_and_send_reminders, "cron", minute="*", id="reminders")
    scheduler.add_job(send_feedback_requests, "cron", hour=12, minute=0, id="feedback_requests")
    scheduler.add_job(save_daily_sessions, "cron", hour=0, minute=5, id="save_daily_sessions")
    scheduler.start()
    logger.info("Scheduler started")
