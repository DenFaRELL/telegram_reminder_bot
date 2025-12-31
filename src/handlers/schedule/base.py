# src/handlers/schedule/base.py
"""Базовые функции для работы с расписанием"""

import re
from typing import Optional, Tuple

from src.database import get_connection


def validate_subject(subject: str) -> tuple[bool, str]:
    """Проверка названия предмета"""
    if not subject or not subject.strip():
        return False, "Название предмета не может быть пустым"
    if len(subject.strip()) > 100:
        return False, "Название предмета слишком длинное (макс. 100 символов)"
    return True, ""


def validate_time(
    time_str: str,
) -> Tuple[bool, Optional[str], Optional[Tuple[str, str]]]:
    """
    Проверяет корректность формата времени.
    Формат: 'HH:MM-HH:MM'

    Возвращает:
        (is_valid, error_message, (start_time, end_time))
    """
    if not time_str:
        return False, "❌ Время не может быть пустым", None

    if "-" not in time_str:
        return False, "❌ Неправильный формат времени. Используйте: '09:00-10:30'", None

    try:
        start_str, end_str = time_str.split("-")

        # Проверяем формат времени (две цифры, двоеточие, две цифры)
        time_pattern = r"^\d{2}:\d{2}$"
        if not re.match(time_pattern, start_str) or not re.match(time_pattern, end_str):
            return (
                False,
                "❌ Неправильный формат времени. Используйте: '09:00-10:30'",
                None,
            )

        # Парсим часы и минуты
        start_hour, start_minute = map(int, start_str.split(":"))
        end_hour, end_minute = map(int, end_str.split(":"))

        # Проверяем корректность часов (0-23) и минут (0-59)
        if not (0 <= start_hour <= 23):
            return False, f"❌ Часы начала должны быть от 00 до 23: {start_hour}", None
        if not (0 <= start_minute <= 59):
            return (
                False,
                f"❌ Минуты начала должны быть от 00 до 59: {start_minute}",
                None,
            )
        if not (0 <= end_hour <= 23):
            return False, f"❌ Часы окончания должны быть от 00 до 23: {end_hour}", None
        if not (0 <= end_minute <= 59):
            return (
                False,
                f"❌ Минуты окончания должны быть от 00 до 59: {end_minute}",
                None,
            )

        # Проверяем что начальное время раньше конечного
        # Конвертируем время в минуты для сравнения
        start_total_minutes = start_hour * 60 + start_minute
        end_total_minutes = end_hour * 60 + end_minute

        if start_total_minutes >= end_total_minutes:
            return (
                False,
                f"❌ Время начала ({start_str}) должно быть раньше времени окончания ({end_str})",
                None,
            )

        # Все проверки пройдены
        return True, "", (start_str, end_str)

    except ValueError as e:
        return False, f"❌ Ошибка разбора времени: {str(e)}", None


def validate_build(build: str) -> tuple[bool, str]:
    """Проверка номера корпуса"""
    if not build or build.lower() == "нет":
        return True, ""

    if not build.isdigit():
        return False, "Номер корпуса должен состоять только из цифр"

    if len(build) > 10:
        return False, "Номер корпуса слишком длинный"

    return True, ""


def validate_room(room: str) -> tuple[bool, str]:
    """Проверка номера аудитории"""
    if not room or room.lower() == "нет":
        return True, ""

    if not room.isdigit():
        return False, "Номер аудитории должен состоять только из цифр"

    if len(room) > 10:
        return False, "Номер аудитории слишком длинный"

    return True, ""


def validate_teacher(teacher: str) -> tuple[bool, str]:
    """Проверка ФИО преподавателя"""
    if not teacher or teacher.lower() == "нет":
        return True, ""

    # Разрешаем буквы, пробелы, дефисы, точки и запятые
    name_pattern = r"^[А-Яа-яЁёA-Za-z\s\-\.,]+$"
    if not re.match(name_pattern, teacher):
        return False, "ФИО должно содержать только буквы, пробелы, дефисы и точки"

    if len(teacher.strip()) < 2:
        return False, "ФИО слишком короткое"

    if len(teacher) > 100:
        return False, "ФИО слишком длинное"

    return True, ""


def save_lesson(user_id: int, data: dict) -> tuple[bool, int, str]:
    """Сохранение урока в базу данных"""
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
                data.get("teacher"),
            ),
        )
        conn.commit()
        lesson_id = cursor.lastrowid
        return True, lesson_id, "Урок успешно сохранен"

    except Exception as e:
        return False, 0, f"Ошибка при сохранении: {str(e)}"

    finally:
        conn.close()


def update_lesson(lesson_id: int, field: str, value) -> tuple[bool, str]:
    """Обновление поля урока"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if field == "time":
            start_time, end_time = value
            cursor.execute(
                "UPDATE schedule SET start_time = ?, end_time = ? WHERE id = ?",
                (start_time, end_time, lesson_id),
            )
        else:
            # Для пустых значений ставим None
            if value is None or (isinstance(value, str) and value.lower() == "нет"):
                value = None

            if field == "subject":
                cursor.execute(
                    "UPDATE schedule SET subject = ? WHERE id = ?", (value, lesson_id)
                )
            elif field == "build":
                cursor.execute(
                    "UPDATE schedule SET build = ? WHERE id = ?", (value, lesson_id)
                )
            elif field == "room":
                cursor.execute(
                    "UPDATE schedule SET room = ? WHERE id = ?", (value, lesson_id)
                )
            elif field == "teacher":
                cursor.execute(
                    "UPDATE schedule SET teacher = ? WHERE id = ?", (value, lesson_id)
                )
            elif field == "day":
                cursor.execute(
                    "UPDATE schedule SET day_of_week = ? WHERE id = ?",
                    (value, lesson_id),
                )

        conn.commit()
        return True, "Поле успешно обновлено"

    except Exception as e:
        return False, f"Ошибка при обновлении: {str(e)}"

    finally:
        conn.close()


def get_lesson(lesson_id: int):
    """Получение урока по ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schedule WHERE id = ?", (lesson_id,))
    lesson = cursor.fetchone()
    conn.close()

    if lesson:
        return dict(lesson)
    return None


def get_user_lessons(user_id: int):
    """Получение уроков пользователя"""
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
    return lessons


def delete_lesson(lesson_id: int) -> bool:
    """Удаление урока"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM schedule WHERE id = ?", (lesson_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def format_lesson_details(lesson: dict) -> str:
    """Форматирование деталей урока для отображения"""
    response = "📚 <b>Детали урока:</b>\n\n"
    response += f"📅 <b>День недели:</b> {lesson['day_of_week']}\n"
    response += f"🕒 <b>Время:</b> {lesson['start_time']} - {lesson['end_time']}\n"
    response += f"📖 <b>Предмет:</b> {lesson['subject']}\n"

    if lesson.get("build"):
        response += f"🏢 <b>Корпус:</b> {lesson['build']}\n"
    if lesson.get("room"):
        response += f"🚪 <b>Аудитория:</b> {lesson['room']}\n"
    if lesson.get("teacher"):
        response += f"👨‍🏫 <b>Преподаватель:</b> {lesson['teacher']}\n"

    return response
