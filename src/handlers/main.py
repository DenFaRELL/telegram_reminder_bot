# src/handlers/main.py
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.database import get_connection
from src.handlers.events import show_events_list
from src.handlers.schedule import show_schedule
from src.handlers.tasks import show_tasks_list
from src.keyboards import get_main_keyboard

router = Router()

# Словарь для хранения текущего раздела пользователя
user_current_section = {}

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Начало работы - главное меню"""
    user_id = message.from_user.id
    conn = get_connection()
    cursor = conn.cursor()

    # Регистрируем пользователя
    cursor.execute(
        """
        INSERT OR IGNORE INTO users (telegram_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        ),
    )
    conn.commit()
    conn.close()

    # Сбрасываем раздел
    user_current_section[user_id] = "main"

    await message.answer(
        "👋 <b>Привет! Я бот-напоминалка для студентов!</b>\n\n"
        "📌 <b>Что я умею:</b>\n"
        "• 📅 Вести расписание занятий\n"
        "• ✅ Создавать список задач с дедлайнами\n"
        "• 🎯 Напоминать о событиями\n\n"
        "📌 <b>Используйте кнопки внизу:</b>",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


# ==================== НАВИГАЦИЯ ====================

@router.message(Command("menu"))
@router.message(F.text == "🔙 Назад")
async def cmd_menu(message: Message):
    """Вернуться в главное меню"""
    user_id = message.from_user.id
    user_current_section[user_id] = "main"

    await message.answer(
        "📱 <b>Главное меню</b>\n\nВыберите раздел:",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


# ==================== РАЗДЕЛ РАСПИСАНИЯ ====================

@router.message(F.text == "📅 Расписание")
async def button_schedule_menu(message: Message):
    """Переход в раздел Расписание"""
    user_id = message.from_user.id
    user_current_section[user_id] = "schedule"
    await show_schedule(message, user_id)


# ==================== РАЗДЕЛ ЗАДАЧ ====================

@router.message(F.text == "✅ Задачи")
async def button_tasks_menu(message: Message):
    """Переход в раздел Задачи"""
    user_id = message.from_user.id
    user_current_section[user_id] = "tasks"
    await show_tasks_list(message, user_id)


# ==================== РАЗДЕЛ СОБЫТИЙ ====================

@router.message(F.text == "🎯 События")
async def button_events_menu(message: Message):
    """Переход в раздел Событий"""
    user_id = message.from_user.id
    user_current_section[user_id] = "events"

    # Показываем список событий с inline-кнопками
    await show_events_list(message, user_id)


    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM events WHERE user_id = ?", (user_id,))
    events_count = cursor.fetchone()[0]
    conn.close()

    if events_count == 0:
        response = "🎯 <b>У вас пока нет событий!</b>\n\nДобавьте первое событие командой /add_event"
    else:
        response = f"🎯 <b>Раздел событий</b>\n\n"
        response += f"📊 <b>Статистика:</b>\n"
        response += f"• Всего событий: {events_count}\n\n"
        response += "<b>Доступные команды:</b>\n"
        response += "• /show_events - показать все события\n"
        response += "• /add_event - добавить новое событие\n"
        response += "• /upcoming_events - ближайшие события"

    await message.answer(response, reply_markup=get_main_keyboard(), parse_mode="HTML")


# ==================== СТАТИСТИКА ====================

@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message):
    """Статистика"""
    user_id = message.from_user.id
    user_current_section[user_id] = "main"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_completed = FALSE", (user_id,))
    active_tasks = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM events WHERE user_id = ?", (user_id,))
    events_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM schedule WHERE user_id = ?", (user_id,))
    schedule_count = cursor.fetchone()[0]
    conn.close()

    await message.answer(
        f"📊 <b>Ваша статистика:</b>\n\n"
        f"• Активных задач: {active_tasks}\n"
        f"• Событий: {events_count}\n"
        f"• Уроков в расписании: {schedule_count}",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


# ==================== ПОМОЩЬ ====================

@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def show_context_help(message: Message):
    """Показать контекстную помощь"""
    user_id = message.from_user.id
    current_section = user_current_section.get(user_id, "main")

    if current_section == "schedule":
        await show_schedule_help(message)
    elif current_section == "tasks":
        await show_tasks_help(message)
    elif current_section == "events":
        await show_events_help(message)
    else:
        await show_main_help(message)


async def show_main_help(message: Message):
    """Общая помощь"""
    await message.answer(
        "🆘 <b>Общая справка:</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - начать работу с ботом\n"
        "/menu - вернуться в главное меню\n"
        "/add_lesson - добавить новый урок\n"
        "/add_task - добавить новую задачу\n"
        "/add_event - добавить новое событие\n"
        "/stats - статистика\n\n"
        "<b>Основные разделы:</b>\n"
        "• <b>Расписание</b> - управление расписанием занятий\n"
        "• <b>Задачи</b> - управление задачами и дедлайнами\n"
        "• <b>События</b> - управление событиями и напоминаниями\n"
        "• <b>Статистика</b> - ваша активность",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


async def show_schedule_help(message: Message):
    """Помощь по разделу расписания"""
    await message.answer(
        "📚 <b>Помощь по разделу 'Расписание':</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/add_lesson - добавить новый урок\n"
        "/edit_lesson - редактировать существующий урок\n"
        "/delete_lesson - удалить урок\n\n"
        "<b>Как добавить урок:</b>\n"
        "1. Используйте команду /add_lesson\n"
        "2. Выберите день недели\n"
        "3. Введите название предмета\n"
        "4. Введите время (например: 10:00-11:35)\n"
        "5. Введите корпус (или 'нет')\n"
        "6. Введите аудиторию (или 'нет')\n"
        "7. Введите преподавателя (или 'нет')\n\n"
        "<b>Формат времени:</b> ЧЧ:ММ-ЧЧ:ММ (пример: 08:30-10:05)",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


async def show_tasks_help(message: Message):
    """Помощь по разделу задач"""
    await message.answer(
        "📝 <b>Помощь по разделу 'Задачи':</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/show_tasks - показать все задачи\n"
        "/add_task - добавить новую задачу\n"
        "/complete_task - отметить задачу как выполненную\n"
        "/urgent_tasks - показать срочные задачи\n"
        "/task_stats - статистика по задачам\n\n"
        "<b>Что такое срочные задачи?</b>\n"
        "Это задачи с дедлайном меньше 7 дней\n\n"
        "<b>Формат дедлайна:</b> ГГГГ-ММ-ДД (пример: 2024-12-31)",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


async def show_events_help(message: Message):
    """Помощь по разделу событий"""
    await message.answer(
        "🎯 <b>Помощь по разделу 'События':</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/show_events - показать все события\n"
        "/add_event - добавить новое событие\n"
        "/upcoming_events - ближайшие события (7 дней)\n\n"
        "<b>Что такое повторяющиеся события?</b>\n"
        "События, которые происходят регулярно:\n"
        "• Еженедельно - каждую неделю\n"
        "• Ежемесячно - каждый месяц\n"
        "• Ежегодно - каждый год\n\n"
        "<b>Формат даты и времени:</b> ГГГГ-ММ-ДД ЧЧ:ММ (пример: 2024-12-31 18:30)",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


# ==================== КОМАНДЫ ДЛЯ АВТОПОДСКАЗОК ====================

@router.message(Command("add_lesson"))
async def cmd_add_lesson_via_command(message: Message):
    """Добавление урока через команду"""
    from src.handlers.schedule import cmd_add_lesson
    await cmd_add_lesson(message)


@router.message(Command("add_task"))
async def cmd_add_task_via_command(message: Message):
    """Добавление задачи через команду"""
    from aiogram.fsm.context import FSMContext

    from src import bot
    from src.handlers.tasks import add_task_handler

    user_id = message.from_user.id
    user_current_section[user_id] = "tasks"
    state = FSMContext(bot.storage, message.chat.id, message.from_user.id)
    await add_task_handler(message, state)


@router.message(Command("add_event"))
async def cmd_add_event_via_command(message: Message):
    """Добавление события через команду"""
    await message.answer(
        "🎯 <b>Добавление события</b>\n\n"
        "Эта функция скоро будет доступна!",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )
