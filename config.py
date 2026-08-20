"""
Конфигурация бота. Значения берутся из переменных окружения (.env).
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "bot.db")

# Ссылка на диагностическую сессию больше не нужна (TidyCal убран) -
# бот сам ведёт слоты через БД и админ-команды.
