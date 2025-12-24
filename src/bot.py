import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот-напоминалка!\n"
        "Я помогу с:\n"
        "📅 Расписанием пар\n"
        "✅ Списком дел\n"
        "🔔 Напоминаниями\n\n"
        "Используй /help для списка команд"
    )

# Обработчик команды /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    commands = [
        "/start - Начало работы",
        "/help - Список команд",
        "/schedule - Моё расписание",
        "/add_task - Добавить задачу",
        "/tasks - Мои задачи",
        "/add_event - Добавить событие",
        "/events - Мои события"
    ]
    await message.answer("📋 Доступные команды:\n" + "\n".join(commands))

# Основная функция
async def main():
    logging.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())