import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from app.config import settings
from app.scheduler import start_scheduler
from bot.handlers import start, pet_creation, nutrition, reminders, ai_handler, weight

logging.basicConfig(level=logging.INFO)


async def main():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)
    dp.include_router(start.router)
    dp.include_router(pet_creation.router)
    dp.include_router(nutrition.router)
    dp.include_router(reminders.router)
    dp.include_router(ai_handler.router)
    dp.include_router(weight.router)
    start_scheduler(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
