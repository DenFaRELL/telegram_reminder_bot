# src/bot.py
import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("BOT_TOKEN не найден в переменных окружения!")
    exit(1)

# Создаем экземпляры бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Импортируем и подключаем роутеры
try:
    from src.handlers import events_router, main_router, schedule_router, tasks_router

    dp.include_router(main_router)
    dp.include_router(schedule_router)
    dp.include_router(tasks_router)
    dp.include_router(events_router)

    logging.info("✅ Роутеры успешно подключены")

except ImportError as e:
    logging.error(f"❌ Ошибка импорта роутеров: {e}")
    logging.error("Проверьте структуру файлов и импорты")
    sys.exit(1)


async def main():
    """Основная функция запуска бота"""
    logging.info("Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
