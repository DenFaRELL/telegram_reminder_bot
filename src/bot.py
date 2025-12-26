# src/bot.py
import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from dotenv import load_dotenv

# Добавляем пути для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импорты
from database import get_connection, init_database
from keyboards import (
    get_main_keyboard,
    get_back_help_keyboard,
    get_add_lesson_keyboard,
    get_schedule_actions_keyboard,
    get_schedule_actions_empty_keyboard
)

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
dp = Dispatcher()

# Инициализация базы данных
init_database()

# Состояния для добавления урока
class AddLessonStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_time = State()
    waiting_for_build = State()
    waiting_for_room = State()
    waiting_for_teacher = State()


# Словарь для хранения текущего раздела пользователя
user_current_section = {}


# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

@dp.message(Command("start"))
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

@dp.message(Command("menu"))
@dp.message(F.text == "🔙 Назад")
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

@dp.message(F.text == "📅 Расписание")
async def button_schedule_menu(message: Message):
    """Переход в раздел Расписание и показ расписания"""
    user_id = message.from_user.id
    user_current_section[user_id] = "schedule"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT subject, day_of_week, start_time, end_time, build, room, teacher
        FROM schedule
        WHERE user_id = ?
        ORDER BY
            CASE day_of_week
                WHEN 'Понедельник' THEN 1
                WHEN 'Вторник' THEN 2
                WHEN 'Среда' THEN 3
                WHEN 'Четверг' THEN 4
                WHEN 'Пятница' THEN 5
                WHEN 'Суббота' THEN 6
                ELSE 7
            END,
            start_time
        """,
        (user_id,)
    )

    lessons = cursor.fetchall()
    conn.close()

    if not lessons:
        # Если расписание пустое - просто показываем сообщение
        await message.answer(
            "📅 <b>Ваше расписание пусто!</b>",
            parse_mode="HTML"
        )
        # Показываем кнопку для добавления первого урока
        await message.answer(
            "Добавьте первый урок:",
            reply_markup=get_schedule_actions_empty_keyboard(),
            parse_mode="HTML"
        )
    else:
        # Показываем расписание с красивым форматированием
        response = "📅 <b>Ваше расписание:</b>\n\n"

        current_day = None
        for subject, day, start_time, end_time, build, room, teacher in lessons:
            if day != current_day:
                if current_day is not None:
                    response += "\n"
                # День недели - крупно и по центру
                response += f"<b>───────── {day} ─────────</b>\n\n"
                current_day = day

            # 1 строка: время
            response += f"🕒 <b>{start_time} - {end_time}</b>\n"

            # 2 строка: название предмета
            response += f"<b>{subject}</b>\n"

            # 3 строка: корпус и аудитория
            location_parts = []
            if build:
                location_parts.append(f"🏢 Корпус {build}")
            if room:
                location_parts.append(f"🚪 Ауд. {room}")

            if location_parts:
                response += f"<i>{' • '.join(location_parts)}</i>\n"

            # 4 строка: преподаватель
            if teacher:
                response += f"👨‍🏫 <i>{teacher}</i>\n"

            response += "\n"  # Отступ между занятиями

        # Отправляем сообщение с расписанием
        await message.answer(
            response,
            parse_mode="HTML"
        )

        # Отправляем кнопки действий под расписанием
        await message.answer(
            "Управление расписанием:",
            reply_markup=get_schedule_actions_keyboard(),
            parse_mode="HTML"
        )

    # Показываем кнопки навигации
    await message.answer(
        "Используйте кнопки ниже:",
        reply_markup=get_back_help_keyboard(),
        parse_mode="HTML"
    )


# ==================== РАЗДЕЛ ЗАДАЧ ====================

@dp.message(F.text == "✅ Задачи")
async def button_tasks_menu(message: Message):
    """Переход в раздел Задачи"""
    user_id = message.from_user.id
    user_current_section[user_id] = "tasks"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) FROM tasks WHERE user_id = ?
        """,
        (user_id,)
    )

    tasks_count = cursor.fetchone()[0]
    conn.close()

    if tasks_count == 0:
        response = "✅ <b>У вас пока нет задач!</b>\n\n"
        response += "Добавьте первую задачу командой /add_task"
    else:
        cursor.execute(
            """
            SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_completed = FALSE
            """,
            (user_id,)
        )
        active_tasks = cursor.fetchone()[0]

        response = f"✅ <b>Раздел задач</b>\n\n"
        response += f"📊 <b>Статистика:</b>\n"
        response += f"• Всего задач: {tasks_count}\n"
        response += f"• Активных задач: {active_tasks}\n"
        response += f"• Завершённых задач: {tasks_count - active_tasks}\n\n"
        response += "<b>Доступные команды:</b>\n"
        response += "• /show_tasks - показать все задачи\n"
        response += "• /add_task - добавить новую задачу\n"
        response += "• /urgent_tasks - срочные задачи"

    await message.answer(
        response,
        reply_markup=get_back_help_keyboard(),
        parse_mode="HTML",
    )


# ==================== РАЗДЕЛ СОБЫТИЙ ====================

@dp.message(F.text == "🎯 События")
async def button_events_menu(message: Message):
    """Переход в раздел События"""
    user_id = message.from_user.id
    user_current_section[user_id] = "events"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) FROM events WHERE user_id = ?
        """,
        (user_id,)
    )

    events_count = cursor.fetchone()[0]
    conn.close()

    if events_count == 0:
        response = "🎯 <b>У вас пока нет событий!</b>\n\n"
        response += "Добавьте первое событие командой /add_event"
    else:
        response = f"🎯 <b>Раздел событий</b>\n\n"
        response += f"📊 <b>Статистика:</b>\n"
        response += f"• Всего событий: {events_count}\n\n"
        response += "<b>Доступные команды:</b>\n"
        response += "• /show_events - показать все события\n"
        response += "• /add_event - добавить новое событие\n"
        response += "• /upcoming_events - ближайшие события"

    await message.answer(
        response,
        reply_markup=get_back_help_keyboard(),
        parse_mode="HTML",
    )


# ==================== СТАТИСТИКА (оставляем главную клавиатуру) ====================

@dp.message(Command("stats"))
@dp.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message):
    """Статистика - остаёмся с главной клавиатурой"""
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
        f"• Уроков в расписании: {schedule_count}\n\n"
        f"<i>Используйте кнопки ниже для навигации</i>",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


# ==================== ПОМОЩЬ ====================

@dp.message(Command("help"))
@dp.message(F.text == "❓ Помощь")
async def show_context_help(message: Message):
    """Показать контекстную помощь в зависимости от раздела"""
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
    """Общая помощь (главное меню)"""
    await message.answer(
        "🆘 <b>Общая справка:</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - начать работу с ботом\n"
        "/menu - вернуться в главное меню\n\n"
        "<b>Основные разделы:</b>\n"
        "• <b>Расписание</b> - управление расписанием занятий\n"
        "• <b>Задачи</b> - управление задачами и дедлайнами\n"
        "• <b>События</b> - управление событиями и напоминаниями\n"
        "• <b>Статистика</b> - ваша активность\n\n"
        "<i>В каждом разделе кнопка '❓ Помощь' покажет справку по текущему разделу</i>",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


async def show_schedule_help(message: Message):
    """Помощь по разделу расписания"""
    await message.answer(
        "📚 <b>Помощь по разделу 'Расписание':</b>\n\n"
        "<b>Основные команды:</b>\n"
        "• /add_lesson - добавить новый урок\n"
        "• /edit_lesson - редактировать существующий урок\n"
        "• /delete_lesson - удалить урок\n\n"
        "<b>Как добавить урок:</b>\n"
        "1. Используйте команду /add_lesson\n"
        "2. Выберите день недели\n"
        "3. Введите название предмета\n"
        "4. Введите время (например: 10:00-11:35)\n"
        "5. Введите корпус (или 'нет')\n"
        "6. Введите аудиторию (или 'нет')\n"
        "7. Введите преподавателя (или 'нет')\n\n"
        "<b>Формат времени:</b> ЧЧ:ММ-ЧЧ:ММ (пример: 08:30-10:05)",
        reply_markup=get_back_help_keyboard(),
        parse_mode="HTML",
    )


async def show_tasks_help(message: Message):
    """Помощь по разделу задач"""
    await message.answer(
        "📝 <b>Помощь по разделу 'Задачи':</b>\n\n"
        "<b>Основные команды:</b>\n"
        "• /show_tasks - показать все задачи\n"
        "• /add_task - добавить новую задачу\n"
        "• /urgent_tasks - показать срочные задачи\n"
        "• /task_stats - статистика по задачам\n\n"
        "<b>Что такое срочные задачи?</b>\n"
        "Это задачи с дедлайном меньше 7 дней\n\n"
        "<b>Формат дедлайна:</b> ГГГГ-ММ-ДД (пример: 2024-12-31)",
        reply_markup=get_back_help_keyboard(),
        parse_mode="HTML",
    )


async def show_events_help(message: Message):
    """Помощь по разделу событий"""
    await message.answer(
        "🎯 <b>Помощь по разделу 'События':</b>\n\n"
        "<b>Основные команды:</b>\n"
        "• /show_events - показать все события\n"
        "• /add_event - добавить новое событие\n"
        "• /upcoming_events - ближайшие события (7 дней)\n\n"
        "<b>Что такое повторяющиеся события?</b>\n"
        "События, которые происходят регулярно:\n"
        "• Еженедельно - каждую неделю\n"
        "• Ежемесячно - каждый месяц\n"
        "• Ежегодно - каждый год\n\n"
        "<b>Формат даты и времени:</b> ГГГГ-ММ-ДД ЧЧ:ММ (пример: 2024-12-31 18:30)",
        reply_markup=get_back_help_keyboard(),
        parse_mode="HTML",
    )


# ==================== ОБРАБОТЧИКИ INLINE КНОПОК ДЛЯ РАСПИСАНИЯ ====================

@dp.callback_query(F.data == "add_lesson_btn")
@dp.message(Command("add_lesson"))
async def cmd_add_lesson(message_or_callback):
    """Начать добавление урока"""
    if isinstance(message_or_callback, CallbackQuery):
        message = message_or_callback.message
        user_id = message_or_callback.from_user.id
        await message_or_callback.answer()
    else:
        message = message_or_callback
        user_id = message.from_user.id

    user_current_section[user_id] = "schedule"

    await message.answer(
        "📝 <b>Добавление нового урока</b>\n\n"
        "Выберите день недели:",
        reply_markup=get_add_lesson_keyboard(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "edit_lessons_btn")
async def edit_lessons_handler(callback: CallbackQuery):
    """Редактирование уроков"""
    await callback.answer("Функция редактирования в разработке")
    await callback.message.answer(
        "🔄 <b>Редактирование уроков</b>\n\n"
        "Скоро здесь можно будет редактировать ваши уроки.\n"
        "Пока используйте команду /add_lesson для добавления новых уроков.",
        reply_markup=get_back_help_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "delete_lessons_btn")
async def delete_lessons_handler(callback: CallbackQuery):
    """Удаление уроков"""
    await callback.answer("Функция удаления в разработке")
    await callback.message.answer(
        "🗑️ <b>Удаление уроков</b>\n\n"
        "Скоро здесь можно будет удалять ваши уроки.\n"
        "Пока используйте команду /add_lesson для добавления новых уроков.",
        reply_markup=get_back_help_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("add_lesson_day_"))
async def process_add_lesson_day(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора дня недели для добавления урока"""
    user_current_section[callback.from_user.id] = "schedule"
    day = callback.data.split("_")[3]  # Получаем день из callback_data

    # Сохраняем день в состоянии
    await state.update_data(day=day)

    await callback.message.answer(
        f"📅 <b>Выбран день:</b> {day}\n\n"
        "📚 <b>Введите название предмета:</b>\n"
        "<i>Например: Математика, Физика, Программирование</i>",
        reply_markup=get_back_help_keyboard(),
        parse_mode="HTML"
    )

    await state.set_state(AddLessonStates.waiting_for_subject)
    await callback.answer(f"Выбран день: {day}")


# ==================== ОБРАБОТЧИКИ СОСТОЯНИЙ ДЛЯ ДОБАВЛЕНИЯ УРОКА ====================

@dp.message(AddLessonStates.waiting_for_subject)
async def process_lesson_subject(message: Message, state: FSMContext):
    """Обработка названия предмета"""
    await state.update_data(subject=message.text)
    await message.answer(
        "⏰ <b>Введите время занятия (например: 08:30-10:05):</b>\n"
        "<i>Формат: начало-конец (через дефис)</i>",
        reply_markup=get_back_help_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddLessonStates.waiting_for_time)


@dp.message(AddLessonStates.waiting_for_time)
async def process_lesson_time(message: Message, state: FSMContext):
    """Обработка времени занятия"""
    time_input = message.text.strip()

    if "-" not in time_input:
        await message.answer(
            "❌ <b>Неверный формат!</b>\n"
            "Используйте формат: начало-конец\n"
            "Пример: 08:30-10:05",
            reply_markup=get_back_help_keyboard(),
            parse_mode="HTML"
        )
        return

    try:
        start_time, end_time = time_input.split("-")
        start_time = start_time.strip()
        end_time = end_time.strip()

        # Простая проверка формата времени
        if ":" not in start_time or ":" not in end_time:
            raise ValueError

    except:
        await message.answer(
            "❌ <b>Неверный формат времени!</b>\n"
            "Используйте формат: ЧЧ:ММ-ЧЧ:ММ\n"
            "Пример: 08:30-10:05",
            reply_markup=get_back_help_keyboard(),
            parse_mode="HTML"
        )
        return

    await state.update_data(start_time=start_time, end_time=end_time)
    await message.answer(
        "🏢 <b>Введите номер корпуса (или 'нет'):</b>",
        reply_markup=get_back_help_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddLessonStates.waiting_for_build)


@dp.message(AddLessonStates.waiting_for_build)
async def process_lesson_build(message: Message, state: FSMContext):
    """Обработка корпуса"""
    build = message.text.strip()
    if build.lower() == "нет" or not build:
        build = None

    await state.update_data(build=build)
    await message.answer(
        "🚪 <b>Введите номер аудитории (или 'нет'):</b>",
        reply_markup=get_back_help_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddLessonStates.waiting_for_room)


@dp.message(AddLessonStates.waiting_for_room)
async def process_lesson_room(message: Message, state: FSMContext):
    """Обработка аудитории"""
    room = message.text.strip()
    if room.lower() == "нет" or not room:
        room = None

    await state.update_data(room=room)
    await message.answer(
        "👨‍🏫 <b>Введите ФИО преподавателя (или 'нет'):</b>",
        reply_markup=get_back_help_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddLessonStates.waiting_for_teacher)


@dp.message(AddLessonStates.waiting_for_teacher)
async def process_lesson_teacher(message: Message, state: FSMContext):
    """Обработка преподавателя и сохранение урока"""
    teacher = message.text.strip()
    if teacher.lower() == "нет" or not teacher:
        teacher = None

    # Получаем все данные из состояния
    data = await state.get_data()
    user_id = message.from_user.id

    # Сохраняем урок в базу данных
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO schedule (user_id, subject, day_of_week, start_time, end_time, build, room, teacher)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                data["subject"],
                data["day"],
                data["start_time"],
                data["end_time"],
                data.get("build"),
                data.get("room"),
                teacher,
            )
        )
        conn.commit()

        # Формируем сообщение об успехе
        response = f"✅ <b>Урок добавлен в расписание!</b>\n\n"
        response += f"📅 <b>День:</b> {data['day']}\n"
        response += f"📚 <b>Предмет:</b> {data['subject']}\n"
        response += f"🕒 <b>Время:</b> {data['start_time']}-{data['end_time']}\n"

        if data.get("build"):
            response += f"🏢 <b>Корпус:</b> {data['build']}\n"
        if data.get("room"):
            response += f"🚪 <b>Аудитория:</b> {data['room']}\n"
        if teacher:
            response += f"👨‍🏫 <b>Преподаватель:</b> {teacher}\n"

        response += "\n<i>Нажмите '📅 Расписание' чтобы увидеть обновлённое расписание</i>"

        await message.answer(
            response,
            reply_markup=get_back_help_keyboard(),
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(
            f"❌ <b>Ошибка при сохранении урока:</b>\n{str(e)}",
            parse_mode="HTML"
        )

    finally:
        conn.close()
        await state.clear()  # Очищаем состояние


# ==================== ЗАПУСК ====================

async def main():
    logging.info("Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
