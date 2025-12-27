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
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("BOT_TOKEN не найден в переменных окружения!")
    exit(1)

# Создаем экземпляры бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


def setup_routers():
    """Настройка роутеров - вызывается один раз"""
    # Импортируем роутеры здесь, чтобы избежать циклических импортов
    from src.handlers.main import router as main_router
    from src.handlers.schedule import router as schedule_router
    from src.handlers.tasks import router as tasks_router
    from src.handlers.events import router as events_router

    # Подключаем роутеры
    dp.include_router(main_router)
    dp.include_router(schedule_router)
    dp.include_router(tasks_router)
    dp.include_router(events_router)


# Настраиваем роутеры при импорте модуля
setup_routers()


# ==================== ЗАПУСК ====================


async def main():
    """Основная функция запуска бота"""
    logging.info("Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
