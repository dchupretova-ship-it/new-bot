# -*- coding: utf-8 -*-
"""Точка входа: запуск Telegram-бота "Тест на 5 паттернов" (long polling)."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
import database as db
from handlers import user as user_handlers
from handlers import admin as admin_handlers


async def main():
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN:
        raise RuntimeError(
            "Не задан BOT_TOKEN. Создай файл .env на основе .env.example и укажи токен от @BotFather."
        )

    db.init_db()

    bot = Bot(token=BOT_TOKEN)  # обычный текст, без parse_mode - тексты без разметки
    dp = Dispatcher(storage=MemoryStorage())

    # admin-роутер первым, чтобы команды /addslot и т.п. не перехватывались другими хендлерами
    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
