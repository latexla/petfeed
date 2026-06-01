import asyncio
import os
import signal

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, MenuButtonCommands, MenuButtonWebApp, WebAppInfo

from app.config import settings
from app.observability import setup_observability
from app.scheduler import start_scheduler
from bot.handlers import ai_handler, feedback, food_picker, meal_builder, nutrition, pet_creation, reminders, start, weight

setup_observability("bot")

BOT_COMMANDS = [
    BotCommand(command="start", description="Создать профиль питомца или вернуться в меню"),
    BotCommand(command="help",  description="Что умеет бот и как им пользоваться"),
]


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
    dp.include_router(food_picker.router)
    dp.include_router(feedback.router)
    start_scheduler(bot)
    await bot.set_my_commands(BOT_COMMANDS)
    await _set_menu_button(bot)
    await dp.start_polling(bot, drop_pending_updates=True)


async def _set_menu_button(bot: Bot):
    """Replace the bot's Menu button with a Mini App launcher.

    Opens MINIAPP_URL as a Web App (not a plain url), so Telegram delivers
    initData and миниапп авторизуется. Falls back to the default commands
    menu when MINIAPP_URL is not configured.
    """
    if settings.MINIAPP_URL:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Открыть приложение",
                web_app=WebAppInfo(url=settings.MINIAPP_URL),
            )
        )
    else:
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: os._exit(0))
    asyncio.run(main())
