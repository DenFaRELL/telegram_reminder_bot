# src/handlers/schedule.py
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from src.database import get_connection
from src.keyboards import (
    get_add_lesson_keyboard,
    get_day_selection_keyboard,
    get_delete_confirmation_keyboard,
    get_edit_lesson_keyboard,
    get_lesson_detail_keyboard,
    get_lessons_selection_keyboard,
    get_schedule_list_keyboard,
)
from src.states import AddLessonStates, EditLessonStates

router = Router()

# Глобальная переменная для user_current_section
user_current_section = {}
# Словарь для хранения временного списка уроков по user_id
user_lessons_cache = {}


async def show_schedule(message: Message, user_id):
    """Показать расписание с inline-кнопками для выбора уроков"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, subject, day_of_week, start_time, end_time, build, room, teacher
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
        (user_id,),
    )

    lessons = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Сохраняем уроки в кэш
    user_lessons_cache[user_id] = lessons

    if not lessons:
        response = "📅 <b>Ваше расписание пусто!</b>\n\n"
        response += "Добавьте первый урок с помощью кнопки ниже:"

        await message.answer(
            response,
            reply_markup=get_schedule_list_keyboard(),
            parse_mode="HTML",
        )
    else:
        response = "📅 <b>Ваше расписание:</b>\n\n"
        response += "<i>Выберите урок для просмотра деталей:</i>\n\n"

        current_day = None

        for i, lesson in enumerate(lessons[:5], 1):
            day = lesson["day_of_week"]
            if day != current_day:
                if current_day is not None:
                    response += "\n"
                response += f"<b>───────── {day} ─────────</b>\n\n"
                current_day = day

            subject = lesson["subject"]
            start_time = lesson["start_time"]
            end_time = lesson["end_time"]

            response += f"<b>{i}.</b> {start_time}-{end_time} - {subject}\n"

        await message.answer(
            response,
            reply_markup=get_lessons_selection_keyboard(lessons),
            parse_mode="HTML",
        )


async def show_lesson_details_safe(chat_id, lesson_id, bot):
    """Безопасное отображение деталей урока"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schedule WHERE id = ?", (lesson_id,))
    lesson_result = cursor.fetchone()
    conn.close()

    if not lesson_result:
        return None

    lesson = dict(lesson_result)

    # Формируем детальное описание урока
    response = "📚 <b>Детали урока:</b>\n\n"
    response += f"📅 <b>День недели:</b> {lesson['day_of_week']}\n"
    response += f"🕒 <b>Время:</b> {lesson['start_time']} - {lesson['end_time']}\n"
    response += f"📖 <b>Предмет:</b> {lesson['subject']}\n"

    if lesson["build"]:
        response += f"🏢 <b>Корпус:</b> {lesson['build']}\n"
    if lesson["room"]:
        response += f"🚪 <b>Аудитория:</b> {lesson['room']}\n"
    if lesson["teacher"]:
        response += f"👨‍🏫 <b>Преподаватель:</b> {lesson['teacher']}\n"

    await bot.send_message(
        chat_id=chat_id,
        text=response,
        reply_markup=get_lesson_detail_keyboard(lesson_id),
        parse_mode="HTML",
    )

    return True


@router.callback_query(F.data == "schedule_help_btn")
async def schedule_help_handler(callback: CallbackQuery):
    """Помощь по расписанию"""
    from src.handlers.main import show_schedule_help

    await callback.answer()
    await show_schedule_help(callback.message)


@router.callback_query(F.data == "add_lesson_btn")
@router.message(Command("add_lesson"))
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
        "📝 <b>Добавление нового урока</b>\n\nВыберите день недели:",
        reply_markup=get_add_lesson_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("add_lesson_day_"))
async def process_add_lesson_day(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора дня недели для добавления урока"""
    user_current_section[callback.from_user.id] = "schedule"
    day = callback.data.split("_")[3]

    await state.update_data(day=day)

    await callback.message.answer(
        f"📅 <b>Выбран день:</b> {day}\n\n"
        "📚 <b>Введите название предмета:</b>\n"
        "<i>Например: Математика, Физика, Программирование</i>",
        parse_mode="HTML",
    )

    await state.set_state(AddLessonStates.waiting_for_subject)
    await callback.answer(f"Выбран день: {day}")


@router.message(AddLessonStates.waiting_for_subject)
async def process_lesson_subject(message: Message, state: FSMContext):
    """Обработка названия предмета"""
    if not message.text.strip():
        await message.answer(
            "❌ <b>Название предмета не может быть пустым!</b>\nПожалуйста, введите название:",
            parse_mode="HTML",
        )
        return

    await state.update_data(subject=message.text.strip())
    await message.answer(
        "⏰ <b>Введите время занятия (например: 08:30-10:05):</b>\n"
        "<i>Формат: начало-конец (через дефис)</i>",
        parse_mode="HTML",
    )
    await state.set_state(AddLessonStates.waiting_for_time)


@router.message(AddLessonStates.waiting_for_time)
async def process_lesson_time(message: Message, state: FSMContext):
    """Обработка времени занятия"""
    time_input = message.text.strip()

    if "-" not in time_input:
        await message.answer(
            "❌ <b>Неверный формат!</b>\n"
            "Используйте формат: начало-конец\n"
            "Пример: 08:30-10:05",
            parse_mode="HTML",
        )
        return

    try:
        start_time, end_time = time_input.split("-")
        start_time = start_time.strip()
        end_time = end_time.strip()

        if ":" not in start_time or ":" not in end_time:
            raise ValueError

        # Проверяем формат времени
        time_pattern = r"^([0-1][0-9]|2[0-3]):([0-5][0-9])$"
        if not re.match(time_pattern, start_time) or not re.match(
            time_pattern, end_time
        ):
            raise ValueError

    except:
        await message.answer(
            "❌ <b>Неверный формат времени!</b>\n"
            "Используйте формат: ЧЧ:ММ-ЧЧ:ММ (24-часовой формат)\n"
            "Пример: 08:30-10:05, 14:00-15:35",
            parse_mode="HTML",
        )
        return

    await state.update_data(start_time=start_time, end_time=end_time)
    await message.answer(
        "🏢 <b>Введите номер корпуса (только цифры, или 'нет'):</b>\n"
        "<i>Пример: 1, 2, 5 или 'нет'</i>",
        parse_mode="HTML",
    )
    await state.set_state(AddLessonStates.waiting_for_build)


@router.message(AddLessonStates.waiting_for_build)
async def process_lesson_build(message: Message, state: FSMContext):
    """Обработка корпуса"""
    build = message.text.strip()

    if build.lower() == "нет" or not build:
        build = None
    else:
        # Проверяем, что корпус состоит из цифр
        if not build.isdigit():
            await message.answer(
                "❌ <b>Номер корпуса должен состоять только из цифр!</b>\n"
                "Пожалуйста, введите номер корпуса (только цифры) или 'нет':",
                parse_mode="HTML",
            )
            return

    await state.update_data(build=build)
    await message.answer(
        "🚪 <b>Введите номер аудитории (только цифры, или 'нет'):</b>\n"
        "<i>Пример: 101, 205, 301 или 'нет'</i>",
        parse_mode="HTML",
    )
    await state.set_state(AddLessonStates.waiting_for_room)


@router.message(AddLessonStates.waiting_for_room)
async def process_lesson_room(message: Message, state: FSMContext):
    """Обработка аудитории"""
    room = message.text.strip()

    if room.lower() == "нет" or not room:
        room = None
    else:
        # Проверяем, что аудитория состоит из цифр
        if not room.isdigit():
            await message.answer(
                "❌ <b>Номер аудитории должен состоять только из цифр!</b>\n"
                "Пожалуйста, введите номер аудитории (только цифры) или 'нет':",
                parse_mode="HTML",
            )
            return

    await state.update_data(room=room)
    await message.answer(
        "👨‍🏫 <b>Введите ФИО преподавателя (буквы, пробелы, дефисы и точки, или 'нет'):</b>\n"
        "<i>Пример: Иванов И.И. или 'нет'</i>",
        parse_mode="HTML",
    )
    await state.set_state(AddLessonStates.waiting_for_teacher)


@router.message(AddLessonStates.waiting_for_teacher)
async def process_lesson_teacher(message: Message, state: FSMContext):
    """Обработка преподавателя и сохранение урока"""
    teacher = message.text.strip()

    if teacher.lower() == "нет" or not teacher:
        teacher = None
    else:
        # Проверяем, что ФИО содержит только буквы, пробелы, дефисы и точки
        name_pattern = r"^[А-Яа-яЁёA-Za-z\s\-\.,]+$"
        if not re.match(name_pattern, teacher):
            await message.answer(
                "❌ <b>ФИО преподавателя должно содержать только буквы, пробелы, дефисы и точки!</b>\n"
                "Пожалуйста, введите ФИО преподавателя правильно или 'нет':",
                parse_mode="HTML",
            )
            return

        # Проверяем, что ФИО не слишком короткое
        if len(teacher.strip()) < 2:
            await message.answer(
                "❌ <b>ФИО преподавателя слишком короткое!</b>\n"
                "Пожалуйста, введите полное ФИО преподавателя или 'нет':",
                parse_mode="HTML",
            )
            return

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
            ),
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

        # Показываем детали добавленного урока
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📅 Вернуться к расписанию",
                        callback_data="back_to_schedule",
                    )
                ]
            ]
        )

        await message.answer(response, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        await message.answer(
            f"❌ <b>Ошибка при сохранении урока:</b>\n{str(e)}", parse_mode="HTML"
        )

    finally:
        conn.close()
        await state.clear()


# ==================== ОБРАБОТКА ВЫБОРА УРОКОВ ЧЕРЕЗ INLINE-КНОПКИ ====================


@router.callback_query(F.data.startswith("view_lesson_"))
async def view_lesson_handler(callback: CallbackQuery):
    """Показать детали урока по inline-кнопке"""
    lesson_id = int(callback.data.split("_")[2])
    await callback.answer()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schedule WHERE id = ?", (lesson_id,))
    lesson_result = cursor.fetchone()
    conn.close()

    if not lesson_result:
        await callback.message.answer("❌ Урок не найден!")
        return

    lesson = dict(lesson_result)

    # Формируем детальное описание урока
    response = "📚 <b>Детали урока:</b>\n\n"
    response += f"📅 <b>День недели:</b> {lesson['day_of_week']}\n"
    response += f"🕒 <b>Время:</b> {lesson['start_time']} - {lesson['end_time']}\n"
    response += f"📖 <b>Предмет:</b> {lesson['subject']}\n"

    if lesson["build"]:
        response += f"🏢 <b>Корпус:</b> {lesson['build']}\n"
    if lesson["room"]:
        response += f"🚪 <b>Аудитория:</b> {lesson['room']}\n"
    if lesson["teacher"]:
        response += f"👨‍🏫 <b>Преподаватель:</b> {lesson['teacher']}\n"

    await callback.message.answer(
        response, reply_markup=get_lesson_detail_keyboard(lesson_id), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("lessons_page_"))
async def lessons_page_handler(callback: CallbackQuery):
    """Обработка переключения страниц уроков"""
    start_index = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    await callback.answer()

    lessons = user_lessons_cache.get(user_id, [])

    if not lessons:
        await callback.message.answer("❌ Список уроков пуст!")
        return

    response = "📅 <b>Ваше расписание:</b>\n\n"
    response += "<i>Выберите урок для просмотра деталей:</i>\n\n"

    current_day = None
    displayed_count = 0

    # Находим, с какого урока начать отображение для текущей страницы
    for i in range(start_index, len(lessons)):
        if displayed_count >= 5:
            break

        lesson = lessons[i]
        day = lesson["day_of_week"]
        if day != current_day:
            if current_day is not None and displayed_count > 0:
                response += "\n"
            response += f"<b>───────── {day} ─────────</b>\n\n"
            current_day = day

        subject = lesson["subject"]
        start_time = lesson["start_time"]
        end_time = lesson["end_time"]

        response += f"<b>{i + 1}.</b> {start_time}-{end_time} - {subject}\n"
        displayed_count += 1

    await callback.message.answer(
        response,
        reply_markup=get_lessons_selection_keyboard(lessons, start_index),
        parse_mode="HTML",
    )


# ==================== ОБРАБОТКА РЕДАКТИРОВАНИЯ И УДАЛЕНИЯ УРОКОВ ====================


@router.callback_query(F.data.startswith("edit_lesson_"))
async def edit_lesson_selected(callback: CallbackQuery):
    """Выбран урок для редактирования"""
    lesson_id = int(callback.data.split("_")[2])
    await callback.answer()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schedule WHERE id = ?", (lesson_id,))
    lesson_result = cursor.fetchone()
    conn.close()

    if not lesson_result:
        await callback.message.answer("❌ Урок не найден!")
        return

    lesson = dict(lesson_result)

    # Показываем информацию об уроке и кнопки редактирования
    response = f"✏️ <b>Редактирование урока:</b>\n\n"
    response += f"📅 <b>День:</b> {lesson['day_of_week']}\n"
    response += f"📚 <b>Предмет:</b> {lesson['subject']}\n"
    response += f"🕒 <b>Время:</b> {lesson['start_time']}-{lesson['end_time']}\n"

    if lesson["build"]:
        response += f"🏢 <b>Корпус:</b> {lesson['build']}\n"
    if lesson["room"]:
        response += f"🚪 <b>Аудитория:</b> {lesson['room']}\n"
    if lesson["teacher"]:
        response += f"👨‍🏫 <b>Преподаватель:</b> {lesson['teacher']}\n"

    response += "\n<b>Выберите что изменить:</b>"

    await callback.message.answer(
        response, reply_markup=get_edit_lesson_keyboard(lesson_id), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("delete_lesson_"))
async def delete_lesson_selected(callback: CallbackQuery):
    """Выбран урок для удаления"""
    lesson_id = int(callback.data.split("_")[2])
    await callback.answer()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schedule WHERE id = ?", (lesson_id,))
    lesson_result = cursor.fetchone()
    conn.close()

    if not lesson_result:
        await callback.message.answer("❌ Урок не найден!")
        return

    lesson = dict(lesson_result)

    # Показываем информацию об уроке и кнопку подтверждения
    response = f"🗑️ <b>Удаление урока:</b>\n\n"
    response += f"📅 <b>День:</b> {lesson['day_of_week']}\n"
    response += f"📚 <b>Предмет:</b> {lesson['subject']}\n"
    response += f"🕒 <b>Время:</b> {lesson['start_time']}-{lesson['end_time']}\n"

    if lesson["build"]:
        response += f"🏢 <b>Корпус:</b> {lesson['build']}\n"
    if lesson["room"]:
        response += f"🚪 <b>Аудитория:</b> {lesson['room']}\n"
    if lesson["teacher"]:
        response += f"👨‍🏫 <b>Преподаватель:</b> {lesson['teacher']}\n"

    response += "\n<b>Вы действительно хотите удалить этот урок?</b>"

    await callback.message.answer(
        response,
        reply_markup=get_delete_confirmation_keyboard(lesson_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_lesson(callback: CallbackQuery):
    """Подтверждение удаления урока"""
    lesson_id = int(callback.data.split("_")[2])
    await callback.answer()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedule WHERE id = ?", (lesson_id,))
    conn.commit()
    conn.close()

    await callback.message.answer("✅ Урок удалён!")

    # Показываем обновленный список уроков
    user_id = callback.from_user.id
    user_current_section[user_id] = "schedule"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, subject, day_of_week, start_time, end_time, build, room, teacher
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
        (user_id,),
    )
    lessons = [dict(row) for row in cursor.fetchall()]
    conn.close()

    user_lessons_cache[user_id] = lessons

    if not lessons:
        response = "📅 <b>Ваше расписание пусто!</b>\n\n"
        response += "Добавьте первый урок с помощью кнопки ниже:"

        await callback.message.answer(
            response,
            reply_markup=get_schedule_list_keyboard(),
            parse_mode="HTML",
        )
    else:
        response = "📅 <b>Ваше расписание:</b>\n\n"
        response += "<i>Выберите урок для просмотра деталей:</i>\n\n"

        current_day = None

        for i, lesson in enumerate(lessons[:5], 1):
            day = lesson["day_of_week"]
            if day != current_day:
                if current_day is not None:
                    response += "\n"
                response += f"<b>───────── {day} ─────────</b>\n\n"
                current_day = day

            subject = lesson["subject"]
            start_time = lesson["start_time"]
            end_time = lesson["end_time"]

            response += f"<b>{i}.</b> {start_time}-{end_time} - {subject}\n"

        await callback.message.answer(
            response,
            reply_markup=get_lessons_selection_keyboard(lessons),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("edit_field_"))
async def edit_field_selected(callback: CallbackQuery, state: FSMContext):
    """Выбрано поле для редактирования"""
    data_parts = callback.data.split("_")
    field_name = data_parts[2]
    lesson_id = int(data_parts[3])

    await callback.answer()

    # Сохраняем информацию в состоянии
    await state.update_data(lesson_id=lesson_id, field_name=field_name)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schedule WHERE id = ?", (lesson_id,))
    lesson_result = cursor.fetchone()
    conn.close()

    if not lesson_result:
        await callback.answer("❌ Урок не найден!")
        return

    lesson = dict(lesson_result)

    if field_name == "day":
        await callback.message.answer(
            "📅 <b>Выберите новый день недели:</b>",
            reply_markup=get_day_selection_keyboard(for_edit=True, lesson_id=lesson_id),
            parse_mode="HTML",
        )
    else:
        field_names = {
            "subject": "название предмета",
            "time": "время занятия (формат: 08:30-10:05)",
            "build": "номер корпуса (только цифры, или 'нет')",
            "room": "номер аудитории (только цифры, или 'нет')",
            "teacher": "ФИО преподавателя (буквы, пробелы, дефисы и точки, или 'нет')",
        }

        current_value = lesson.get(field_name, "")
        if field_name == "time":
            current_value = f"{lesson['start_time']}-{lesson['end_time']}"

        message_text = (
            f"✏️ <b>Редактирование {field_names[field_name]}</b>\n\n"
            f"Текущее значение: <code>{current_value if current_value else 'не указано'}</code>\n\n"
            f"<b>Введите новое значение:</b>"
        )

        await callback.message.answer(message_text, parse_mode="HTML")
        await state.set_state(EditLessonStates.waiting_for_field_value)


# ОТДЕЛЬНЫЙ ОБРАБОТЧИК ДЛЯ ВЫБОРА ДНЯ ПРИ РЕДАКТИРОВАНИИ
@router.callback_query(F.data.startswith("select_day_"))
async def select_new_day(callback: CallbackQuery):
    """Выбран новый день недели для редактирования"""
    data_parts = callback.data.split("_")
    new_day = data_parts[2]
    lesson_id = int(data_parts[3])

    await callback.answer(f"Выбран день: {new_day}")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE schedule SET day_of_week = ? WHERE id = ?", (new_day, lesson_id)
    )
    conn.commit()
    conn.close()

    await callback.message.answer(
        f"✅ <b>День недели изменён на {new_day}!</b>", parse_mode="HTML"
    )

    # Показываем кнопку для возврата к уроку
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 Вернуться к уроку",
                    callback_data=f"view_lesson_{lesson_id}",
                )
            ]
        ]
    )

    await callback.message.answer(
        "Нажмите кнопку чтобы вернуться к уроку:", reply_markup=keyboard
    )


@router.message(EditLessonStates.waiting_for_field_value)
async def process_field_value(message: Message, state: FSMContext):
    """Обработка нового значения поля"""
    data = await state.get_data()
    lesson_id = data["lesson_id"]
    field_name = data["field_name"]
    new_value = message.text.strip()

    if not new_value and field_name not in ["build", "room", "teacher"]:
        await message.answer(
            f"❌ <b>Значение не может быть пустым!</b>", parse_mode="HTML"
        )
        return

    conn = get_connection()
    cursor = conn.cursor()

    try:
        if field_name == "time":
            if "-" not in new_value:
                await message.answer(
                    "❌ <b>Неверный формат времени!</b>\nИспользуйте формат: начало-конец\nПример: 08:30-10:05",
                    parse_mode="HTML",
                )
                return

            start_time, end_time = new_value.split("-")
            start_time = start_time.strip()
            end_time = end_time.strip()

            # Проверяем формат времени
            time_pattern = r"^([0-1][0-9]|2[0-3]):([0-5][0-9])$"
            if not re.match(time_pattern, start_time) or not re.match(
                time_pattern, end_time
            ):
                await message.answer(
                    "❌ <b>Неверный формат времени!</b>\n"
                    "Используйте формат: ЧЧ:ММ-ЧЧ:ММ (24-часовой формат)\n"
                    "Пример: 08:30-10:05, 14:00-15:35",
                    parse_mode="HTML",
                )
                return

            cursor.execute(
                "UPDATE schedule SET start_time = ?, end_time = ? WHERE id = ?",
                (start_time, end_time, lesson_id),
            )
        elif field_name == "build":
            if new_value.lower() == "нет" or not new_value:
                new_value = None
            else:
                # Проверяем, что корпус состоит из цифр
                if not new_value.isdigit():
                    await message.answer(
                        "❌ <b>Номер корпуса должен состоять только из цифр!</b>\n"
                        "Пожалуйста, введите номер корпуса (только цифры) или 'нет':",
                        parse_mode="HTML",
                    )
                    return

            cursor.execute(
                "UPDATE schedule SET build = ? WHERE id = ?", (new_value, lesson_id)
            )
        elif field_name == "room":
            if new_value.lower() == "нет" or not new_value:
                new_value = None
            else:
                # Проверяем, что аудитория состоит из цифр
                if not new_value.isdigit():
                    await message.answer(
                        "❌ <b>Номер аудитории должен состоять только из цифр!</b>\n"
                        "Пожалуйста, введите номер аудитории (только цифры) или 'нет':",
                        parse_mode="HTML",
                    )
                    return

            cursor.execute(
                "UPDATE schedule SET room = ? WHERE id = ?", (new_value, lesson_id)
            )
        elif field_name == "teacher":
            if new_value.lower() == "нет" or not new_value:
                new_value = None
            else:
                # Проверяем, что ФИО содержит только буквы, пробелы, дефисы и точки
                name_pattern = r"^[А-Яа-яЁёA-Za-z\s\-\.,]+$"
                if not re.match(name_pattern, new_value):
                    await message.answer(
                        "❌ <b>ФИО преподавателя должно содержать только буквы, пробелы, дефисы и точки!</b>\n"
                        "Пожалуйста, введите ФИО преподавателя правильно или 'нет':",
                        parse_mode="HTML",
                    )
                    return

                # Проверяем, что ФИО не слишком короткое
                if len(new_value.strip()) < 2:
                    await message.answer(
                        "❌ <b>ФИО преподавателя слишком короткое!</b>\n"
                        "Пожалуйста, введите полное ФИО преподавателя или 'нет':",
                        parse_mode="HTML",
                    )
                    return

            cursor.execute(
                "UPDATE schedule SET teacher = ? WHERE id = ?", (new_value, lesson_id)
            )
        elif field_name == "subject":
            if not new_value:
                await message.answer(
                    "❌ <b>Название предмета не может быть пустым!</b>\nПожалуйста, введите название:",
                    parse_mode="HTML",
                )
                return

            cursor.execute(
                "UPDATE schedule SET subject = ? WHERE id = ?", (new_value, lesson_id)
            )

        conn.commit()

        field_display_names = {
            "subject": "Название предмета",
            "time": "Время занятия",
            "build": "Корпус",
            "room": "Аудитория",
            "teacher": "Преподаватель",
        }

        await message.answer(
            f"✅ <b>{field_display_names[field_name]} успешно обновлено!</b>",
            parse_mode="HTML",
        )

        # Получаем обновленные данные урока
        cursor.execute("SELECT * FROM schedule WHERE id = ?", (lesson_id,))
        lesson_result = cursor.fetchone()

        if lesson_result:
            lesson = dict(lesson_result)

            # Формируем детальное описание урока
            response = "📚 <b>Детали урока:</b>\n\n"
            response += f"📅 <b>День недели:</b> {lesson['day_of_week']}\n"
            response += (
                f"🕒 <b>Время:</b> {lesson['start_time']} - {lesson['end_time']}\n"
            )
            response += f"📖 <b>Предмет:</b> {lesson['subject']}\n"

            if lesson["build"]:
                response += f"🏢 <b>Корпус:</b> {lesson['build']}\n"
            if lesson["room"]:
                response += f"🚪 <b>Аудитория:</b> {lesson['room']}\n"
            if lesson["teacher"]:
                response += f"👨‍🏫 <b>Преподаватель:</b> {lesson['teacher']}\n"

            await message.answer(
                response,
                reply_markup=get_lesson_detail_keyboard(lesson_id),
                parse_mode="HTML",
            )

    except Exception as e:
        await message.answer(
            f"❌ <b>Ошибка при обновлении:</b>\n{str(e)}", parse_mode="HTML"
        )
    finally:
        conn.close()
        await state.clear()


@router.callback_query(F.data.startswith("back_to_lesson_"))
async def back_to_lesson(callback: CallbackQuery):
    """Вернуться к деталям урока"""
    lesson_id = int(callback.data.split("_")[3])
    await view_lesson_handler(callback)


@router.callback_query(F.data == "back_to_schedule")
async def back_to_schedule_handler(callback: CallbackQuery):
    """Вернуться к списку расписания"""
    await callback.answer()

    user_id = callback.from_user.id
    user_current_section[user_id] = "schedule"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, subject, day_of_week, start_time, end_time, build, room, teacher
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
        (user_id,),
    )

    lessons = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Сохраняем уроки в кэш
    user_lessons_cache[user_id] = lessons

    if not lessons:
        response = "📅 <b>Ваше расписание пусто!</b>\n\n"
        response += "Добавьте первый урок с помощью кнопки ниже:"

        await callback.message.answer(
            response,
            reply_markup=get_schedule_list_keyboard(),
            parse_mode="HTML",
        )
    else:
        response = "📅 <b>Ваше расписание:</b>\n\n"
        response += "<i>Выберите урок для просмотра деталей:</i>\n\n"

        current_day = None

        for i, lesson in enumerate(lessons[:5], 1):
            day = lesson["day_of_week"]
            if day != current_day:
                if current_day is not None:
                    response += "\n"
                response += f"<b>───────── {day} ─────────</b>\n\n"
                current_day = day

            subject = lesson["subject"]
            start_time = lesson["start_time"]
            end_time = lesson["end_time"]

            response += f"<b>{i}.</b> {start_time}-{end_time} - {subject}\n"

        await callback.message.answer(
            response,
            reply_markup=get_lessons_selection_keyboard(lessons),
            parse_mode="HTML",
        )
