# src/handlers/main.py
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

# Импортируем функции для показа разделов
from src.database import get_connection
from src.keyboards import get_main_keyboard

from .events.main import router as events_router
from .events.view import show_events_list
from .schedule.main import router as schedule_router
from .schedule.main import show_schedule
from .tasks.main import router as tasks_router
from .tasks.main import show_tasks_section

router = Router()

# Словарь для хранения текущего раздела пользователя
user_current_section = {}


def register_routers(dp):
    dp.include_router(schedule_router)
    dp.include_router(tasks_router)
    dp.include_router(events_router)


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
    await show_tasks_section(message, user_id)


# ==================== РАЗДЕЛ СОБЫТИЙ ====================


@router.message(F.text == "🎯 События")
async def button_events_menu(message: Message):
    """Переход в раздел Событий"""
    user_id = message.from_user.id
    user_current_section[user_id] = "events"
    await show_events_list(message, user_id)


# ==================== СТАТИСТИКА ====================


@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message):
    """Статистика"""
    user_id = message.from_user.id
    user_current_section[user_id] = "main"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_completed = FALSE",
        (user_id,),
    )
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
        "/start - начать работы с ботом\n"
        "/menu - вернуться в главное меню\n"
        "/stats - статистика\n\n"
        "<b>Основные разделы:</b>\n"
        "• <b>Расписание</b> - управление расписанием занятий\n"
        "• <b>Задачи</b> - управление задачами и дедлайнами\n"
        "• <b>События</b> - управление событиями и напоминаниями",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


async def show_schedule_help(message: Message):
    """Помощь по разделу расписания"""
    await message.answer(
        "📚 <b>Помощь по разделу 'Расписание':</b>\n\n"
        "<b>Как добавить урок:</b>\n"
        "1. Нажмите '📅 Расписание'\n"
        "2. Нажмите '➕ Добавить урок'\n"
        "3. Выберите день недели\n"
        "4. Введите название предмета\n"
        "5. Введите время (например: 10:00-11:35)\n"
        "6. Введите корпус (или 'нет')\n"
        "7. Введите аудиторию (или 'нет')\n"
        "8. Введите преподавателя (или 'нет')\n\n"
        "<b>Формат времени:</b> ЧЧ:ММ-ЧЧ:ММ (пример: 08:30-10:05)",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


async def show_tasks_help(message: Message):
    """Помощь по разделу задач"""
    await message.answer(
        "📝 <b>Помощь по разделу 'Задачи':</b>\n\n"
        "<b>Как добавить задачу:</b>\n"
        "1. Нажмите '✅ Задачи'\n"
        "2. Нажмите '➕ Добавить задачу'\n"
        "3. Введите название задачи\n"
        "4. Введите описание (или 'нет')\n"
        "5. Введите дедлайн (формат: ГГГГ-ММ-ДД, или 'нет')\n"
        "6. Выберите приоритет\n\n"
        "<b>Формат дедлайна:</b> ГГГГ-ММ-ДД (пример: 2024-12-31)",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


async def show_events_help(message: Message):
    """Помощь по разделу событий"""
    await message.answer(
        "🎯 <b>Помощь по разделу 'События':</b>\n\n"
        "<b>Как добавить событие:</b>\n"
        "1. Нажмите '🎯 События'\n"
        "2. Нажмите '➕ Добавить событие'\n"
        "3. Введите название события\n"
        "4. Введите описание (или 'нет')\n"
        "5. Введите дату и время (формат: ГГГГ-ММ-ДД ЧЧ:ММ)\n"
        "6. Введите место (или 'нет')\n"
        "7. Выберите повторяемость\n\n"
        "<b>Формат даты и времени:</b> ГГГГ-ММ-ДД ЧЧ:ММ (пример: 2024-12-31 18:30)",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


# ==================== КОМАНДЫ ДЛЯ АВТОПОДСКАЗОК ====================


@router.message(Command("add_task"))
async def cmd_add_task_via_command(message: Message, state: FSMContext):
    """Добавление задачи через команду"""
    from src.handlers.tasks.add import add_task_handler_callback

    # Создаем mock callback
    class MockCallback:
        def __init__(self, message):
            self.message = message
            self.from_user = message.from_user
            self.data = "add_task_btn"

        async def answer(self, text=None):
            pass

    mock_callback = MockCallback(message)
    await add_task_handler_callback(mock_callback, state)


@router.message(Command("add_event"))
async def cmd_add_event_via_command(message: Message, state: FSMContext):
    """Добавление события через команду"""
    from src.handlers.events.add import add_event_handler

    # Создаем mock callback
    class MockCallback:
        def __init__(self, message):
            self.message = message
            self.from_user = message.from_user
            self.data = "add_event_btn"

        async def answer(self, text=None):
            pass

    mock_callback = MockCallback(message)
    await add_event_handler(mock_callback, state)


# ==================== ОБРАБОТЧИКИ ДЛЯ INLINE-КНОПОК ====================


@router.callback_query(F.data == "schedule_help_btn")
async def schedule_help_handler(callback: CallbackQuery):
    """Помощь по расписанию через inline-кнопку"""
    await callback.answer()
    await show_schedule_help(callback.message)


@router.callback_query(F.data == "tasks_help_btn")
async def tasks_help_handler(callback: CallbackQuery):
    """Помощь по задачам через inline-кнопку"""
    await callback.answer()
    await show_tasks_help(callback.message)


@router.callback_query(F.data == "events_help_btn")
async def events_help_handler(callback: CallbackQuery):
    """Помощь по событиям через inline-кнопку"""
    await callback.answer()
    await show_events_help(callback.message)


@router.message(Command("test_reminders"))
async def handle_test_reminders(message: Message):
    """Тестирование напоминаний"""
    from src.event_reminders import get_event_reminder_service
    from src.task_reminders import get_task_reminder_service

    await message.answer("🔍 Тестирование напоминаний...")

    # Принудительная проверка
    event_service = get_event_reminder_service()
    task_service = get_task_reminder_service()

    if event_service:
        await event_service.check_upcoming_events()
        await message.answer("✅ Проверка событий выполнена")

    if task_service:
        await task_service.check_upcoming_deadlines()
        await message.answer("✅ Проверка задач выполнена")

    await message.answer("📊 Запущена фоновая отправка напоминаний")


@router.message(Command("test_reminders"))
async def handle_test_reminders(message: Message):
    """Тестирование напоминаний"""
    from src.event_reminders import get_event_reminder_service
    from src.task_reminders import get_task_reminder_service

    await message.answer("🔍 Тестирование напоминаний...")

    # Принудительная проверка
    event_service = get_event_reminder_service()
    task_service = get_task_reminder_service()

    if event_service:
        await event_service.check_upcoming_events()
        await event_service.send_scheduled_reminders()
        await message.answer("✅ Проверка событий выполнена")

    if task_service:
        await task_service.check_upcoming_deadlines()
        await task_service.send_scheduled_reminders()
        await message.answer("✅ Проверка задач выполнена")

    await message.answer("📊 Запущена фоновая отправка напоминаний")
