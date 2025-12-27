# src/bot.py
import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from src.database import init_database

# Добавляем пути для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импорты

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("BOT_TOKEN не найден в переменных окружения!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
init_database()

from src.handlers.events import router as events_router

# Импортируем роутеры после инициализации
from src.handlers.main import router as main_router
from src.handlers.schedule import router as schedule_router
from src.handlers.tasks import router as tasks_router

# Подключаем роутеры
dp.include_router(main_router)
dp.include_router(schedule_router)
dp.include_router(tasks_router)
dp.include_router(events_router)


# ==================== ЗАПУСК ====================

async def main():
    logging.info("Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
