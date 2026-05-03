import asyncio
import logging
import os
import signal
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from app.config import settings
from app.scheduler import start_scheduler
from bot.handlers import start, pet_creation, nutrition, reminders, ai_handler, weight, meal_builder

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
    dp.include_router(meal_builder.router)
    start_scheduler(bot)
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: os._exit(0))
    asyncio.run(main())
