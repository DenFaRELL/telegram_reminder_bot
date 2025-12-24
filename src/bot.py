import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# ==================== ПОСТОЯННАЯ КЛАВИАТУРА ====================

def get_main_keyboard():
    """Создаёт ПОСТОЯННЫЕ кнопки внизу экрана"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Расписание"), KeyboardButton(text="✅ Задачи")],
            [KeyboardButton(text="➕ Добавить задачу"), KeyboardButton(text="🎯 События")],
            [KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,  # Ключевой параметр!
        input_field_placeholder="Выберите действие или введите команду..."
    )

# ==================== КОМАНДА ДЛЯ УДАЛЕНИЯ КЛАВИАТУРЫ ====================

@dp.message(Command("hide"))
async def cmd_hide(message: Message):
    """Убрать клавиатуру"""
    await message.answer(
        "Клавиатура скрыта. Используйте /show чтобы вернуть.",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(Command("show"))
async def cmd_show(message: Message):
    """Показать клавиатуру"""
    await message.answer(
        "Клавиатура возвращена!",
        reply_markup=get_main_keyboard()
    )

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Начало работы с ботом"""
    await message.answer(
        "👋 Привет! Я бот-напоминалка для студентов!\n\n"
        "📌 Кнопки закреплены внизу для удобства.\n"
        "📌 Используйте /hide чтобы убрать кнопки.\n"
        "📌 Используйте /show чтобы вернуть кнопки.",
        reply_markup=get_main_keyboard()  # ПОСТОЯННЫЕ КНОПКИ!
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по командам"""
    help_text = (
        "🆘 **Справка по боту:**\n\n"
        "**Основные команды:**\n"
        "/start - Начать работу\n"
        "/help - Эта справка\n"
        "/hide - Убрать кнопки\n"
        "/show - Вернуть кнопки\n\n"
        "**Или используйте кнопки внизу экрана!**"
    )
    await message.answer(help_text, reply_markup=get_main_keyboard())

# ==================== ОБРАБОТЧИКИ КНОПОК ====================

@dp.message(F.text == "📅 Расписание")
async def button_schedule(message: Message):
    await message.answer("📅 **Функция расписания:**\nПока в разработке...")

@dp.message(F.text == "✅ Задачи")
async def button_tasks(message: Message):
    await message.answer("✅ **Функция задач:**\nПока в разработке...")

@dp.message(F.text == "➕ Добавить задачу")
async def button_add_task(message: Message):
    await message.answer("➕ **Добавление задачи:**\nПока в разработке...")

@dp.message(F.text == "🎯 События")
async def button_events(message: Message):
    await message.answer("🎯 **Функция событий:**\nПока в разработке...")

@dp.message(F.text == "❓ Помощь")
async def button_help(message: Message):
    await cmd_help(message)

# ==================== ЗАПУСК ====================

async def main():
    logging.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
