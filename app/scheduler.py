import logging
import ssl
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
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


def start_scheduler(bot):
    set_bot(bot)
    scheduler.add_job(check_and_send_reminders, "cron", minute="*", id="reminders")
    scheduler.start()
    logger.info("Scheduler started")
