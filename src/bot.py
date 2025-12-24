# src/bot.py
import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем handlers
from handlers.tasks import router as tasks_router
from handlers.events import router as events_router
from handlers.schedule import router as schedule_router
from database import init_db, get_connection

# Импортируем клавиатуры
from keyboard import (
    get_main_keyboard,
    get_schedule_keyboard,
    get_add_lesson_keyboard,
    get_tasks_keyboard,
    get_events_keyboard
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# Подключаем routers
dp.include_router(tasks_router)
dp.include_router(events_router)
dp.include_router(schedule_router)

# Инициализация базы данных
init_db()

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Начало работы"""
    user_id = message.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
    ''', (user_id, message.from_user.username,
          message.from_user.first_name, message.from_user.last_name))
    conn.commit()
    conn.close()
    
    await message.answer(
        "👋 <b>Привет! Я бот-напоминалка для студентов!</b>\n\n"
        "📌 <b>Что я умею:</b>\n"
        "• 📅 Вести расписание пар\n"
        "• ✅ Создавать список задач с дедлайнами\n"
        "• 🎯 Напоминать о событиях\n\n"
        "📌 <b>Используйте кнопки внизу:</b>",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🆘 <b>Справка по командам:</b>\n\n"
        "<b>Основные:</b>\n"
        "/start - начать\n"
        "/help - справка\n"
        "/menu - главное меню\n\n"
        "<b>Задачи:</b>\n"
        "/tasks - список задач\n"
        "/add_task - добавить задачу\n\n"
        "<b>События:</b>\n"
        "/events - список событий\n"
        "/add_event - добавить событие\n\n"
        "<b>Расписание:</b>\n"
        "/schedule - расписание\n"
        "/add_lesson - добавить пару",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

@dp.message(Command("menu"))
@dp.message(F.text == "🔙 Назад в меню")
async def cmd_menu(message: Message):
    """Вернуться в главное меню"""
    await message.answer(
        "📱 <b>Главное меню</b>\n\n"
        "Выберите раздел:",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

@dp.message(Command("stats"))
@dp.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message):
    """Статистика"""
    user_id = message.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_completed = FALSE', (user_id,))
    active_tasks = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM events WHERE user_id = ?', (user_id,))
    events_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM schedule WHERE user_id = ?', (user_id,))
    schedule_count = cursor.fetchone()[0]
    
    conn.close()
    
    await message.answer(
        f"📊 <b>Ваша статистика:</b>\n\n"
        f"• Активных задач: {active_tasks}\n"
        f"• Событий: {events_count}\n"
        f"• Пар в расписании: {schedule_count}",
        parse_mode="HTML"
    )

@dp.message(F.text == "❓ Помощь")
async def button_help(message: Message):
    await cmd_help(message)

# ==================== ПЕРЕКЛЮЧЕНИЕ КЛАВИАТУР ====================

@dp.message(F.text == "📅 Расписание")
async def button_schedule_menu(message: Message):
    """Переключение на клавиатуру расписания"""
    await message.answer(
        "📅 <b>Управление расписанием</b>\n\n"
        "Выберите действие:",
        reply_markup=get_schedule_keyboard(),
        parse_mode="HTML"
    )

@dp.message(F.text == "✅ Задачи")
async def button_tasks_menu(message: Message):
    """Переключение на клавиатуру задач"""
    await message.answer(
        "✅ <b>Управление задачами</b>\n\n"
        "Выберите действие:",
        reply_markup=get_tasks_keyboard(),
        parse_mode="HTML"
    )

@dp.message(F.text == "🎯 События")
async def button_events_menu(message: Message):
    """Переключение на клавиатуру событий"""
    await message.answer(
        "🎯 <b>Управление событиями</b>\n\n"
        "Выберите действие:",
        reply_markup=get_events_keyboard(),
        parse_mode="HTML"
    )

# ==================== ОБРАБОТЧИКИ ДЛЯ КНОПОК РАСПИСАНИЯ ====================

@dp.message(F.text == "➕ Добавить урок")
async def button_add_lesson(message: Message):
    """Обработка кнопки добавления урока"""
    await message.answer(
        "📝 <b>Добавление нового урока</b>\n\n"
        "Выберите день недели:",
        reply_markup=get_add_lesson_keyboard(),
        parse_mode="HTML"
    )

@dp.message(F.text.in_(["📅 Понедельник", "📅 Вторник", "📅 Среда", "📅 Четверг", 
                       "📅 Пятница", "📅 Суббота", "📅 Воскресенье"]))
async def button_select_day(message: Message, state: FSMContext):
    """Обработка выбора дня недели"""
    # Убираем эмодзи из текста
    day = message.text.replace("📅 ", "")
    
    await state.update_data(day=day)
    await message.answer(
        f"📅 <b>Выбран день:</b> {day}\n\n"
        "📚 <b>Введите название предмета:</b>",
        parse_mode="HTML"
    )
    # Состояние будет обработано в schedule.py

@dp.message(F.text == "📋 Показать расписание")
async def button_show_schedule(message: Message):
    """Обработка кнопки показа расписания"""
    from handlers.schedule import show_interactive_schedule
    await show_interactive_schedule(message)

@dp.message(F.text == "✏️ Редактировать урок")
async def button_edit_lesson_action(message: Message):
    """Обработка кнопки редактирования урока"""
    from handlers.schedule import edit_lesson_menu_main
    # Создаем временный callback объект
    class TempCallback:
        def __init__(self, msg):
            self.message = msg
            self.from_user = msg.from_user
            self.data = "edit_lesson_menu"
    
    temp_callback = TempCallback(message)
    await edit_lesson_menu_main(temp_callback)

@dp.message(F.text == "🗑️ Удалить урок")
async def button_delete_lesson_action(message: Message):
    """Обработка кнопки удаления урока"""
    from handlers.schedule import delete_lesson_menu_inline
    # Создаем временный callback объект
    class TempCallback:
        def __init__(self, msg):
            self.message = msg
            self.from_user = msg.from_user
            self.data = "delete_lesson_menu"
    
    temp_callback = TempCallback(message)
    await delete_lesson_menu_inline(temp_callback)

@dp.message(F.text == "❓ Помощь по расписанию")
async def button_schedule_help(message: Message):
    """Помощь по расписанию"""
    await message.answer(
        "📚 <b>Помощь по расписанию:</b>\n\n"
        "<b>Основные функции:</b>\n"
        "• <b>➕ Добавить урок</b> - добавление нового урока\n"
        "• <b>📋 Показать расписание</b> - просмотр всего расписания\n"
        "• <b>✏️ Редактировать урок</b> - изменение параметров урока\n"
        "• <b>🗑️ Удалить урок</b> - удаление урока из расписания\n\n"
        "<b>Как добавить урок:</b>\n"
        "1. Нажмите '➕ Добавить урок'\n"
        "2. Выберите день недели\n"
        "3. Введите название предмета\n"
        "4. Введите время (например: 10:00-11:30)\n"
        "5. Введите аудиторию (или 'нет')\n"
        "6. Введите преподавателя (или 'нет')",
        parse_mode="HTML"
    )

@dp.message(F.text == "🔙 Назад к расписанию")
async def button_back_to_schedule(message: Message):
    """Обработка кнопки назад к расписанию"""
    await message.answer(
        "📅 <b>Управление расписанием</b>\n\n"
        "Выберите действие:",
        reply_markup=get_schedule_keyboard(),
        parse_mode="HTML"
    )

# ==================== ОБРАБОТЧИКИ ДЛЯ КНОПОК ЗАДАЧ ====================

@dp.message(F.text == "📋 Показать задачи")
async def button_show_tasks(message: Message):
    """Обработка кнопки показа задач"""
    from handlers.tasks import show_tasks_from_bot
    await show_tasks_from_bot(message)

@dp.message(F.text == "➕ Новая задача")
async def button_new_task(message: Message, state: FSMContext):
    """Обработка кнопки новой задачи"""
    from handlers.tasks import add_task_command_from_bot
    await add_task_command_from_bot(message, state)

@dp.message(F.text == "🔥 Срочные задачи")
async def button_urgent_tasks(message: Message):
    """Обработка кнопки срочных задач"""
    from handlers.tasks import cmd_urgent_tasks
    await cmd_urgent_tasks(message)

@dp.message(F.text == "📊 Статистика задач")
async def button_tasks_stats(message: Message):
    """Статистика задач"""
    user_id = message.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_completed = FALSE', (user_id,))
    active_tasks = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_completed = TRUE', (user_id,))
    completed_tasks = cursor.fetchone()[0]
    
    # Срочные задачи (дедлайн < 7 дней)
    cursor.execute('''
        SELECT COUNT(*) FROM tasks 
        WHERE user_id = ? AND is_completed = FALSE 
        AND deadline IS NOT NULL 
        AND date(deadline) <= date('now', '+7 days')
    ''', (user_id,))
    urgent_tasks = cursor.fetchone()[0]
    
    conn.close()
    
    await message.answer(
        f"📊 <b>Статистика задач:</b>\n\n"
        f"• Активных задач: {active_tasks}\n"
        f"• Завершённых задач: {completed_tasks}\n"
        f"• Срочных задач (< 7 дней): {urgent_tasks}\n"
        f"• Всего задач: {active_tasks + completed_tasks}",
        parse_mode="HTML"
    )

# ==================== ОБРАБОТЧИКИ ДЛЯ КНОПОК СОБЫТИЙ ====================

@dp.message(F.text == "📅 Показать события")
async def button_show_events(message: Message):
    """Обработка кнопки показа событий"""
    from handlers.events import show_events_from_bot
    await show_events_from_bot(message)

@dp.message(F.text == "➕ Новое событие")
async def button_new_event(message: Message, state: FSMContext):
    """Обработка кнопки нового события"""
    from handlers.events import add_event_command_from_bot
    await add_event_command_from_bot(message, state)

@dp.message(F.text == "🔔 Ближайшие события")
async def button_upcoming_events(message: Message):
    """Обработка кнопки ближайших событий"""
    from handlers.events import show_upcoming_events_from_bot
    await show_upcoming_events_from_bot(message)

@dp.message(F.text == "❓ Помощь по событиям")
async def button_events_help(message: Message):
    """Помощь по событиям"""
    await message.answer(
        "🎯 <b>Помощь по событиям:</b>\n\n"
        "<b>Основные функции:</b>\n"
        "• <b>📅 Показать события</b> - просмотр всех событий\n"
        "• <b>➕ Новое событие</b> - добавление нового события\n"
        "• <b>🔔 Ближайшие события</b> - события на ближайшую неделю\n\n"
        "<b>Как добавить событие:</b>\n"
        "1. Нажмите '➕ Новое событие'\n"
        "2. Введите название события\n"
        "3. Введите дату (ГГГГ-ММ-ДД)\n"
        "4. Введите время (ЧЧ:ММ) или 'нет'",
        parse_mode="HTML"
    )

# ==================== ЗАПУСК ====================

async def main():
    logging.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())