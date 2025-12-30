# src/handlers/events/base.py
"""Базовые функции для работы с событиями"""

from datetime import datetime

from src.database import get_connection


def validate_title(title: str) -> tuple[bool, str]:
    """Проверка названия события"""
    if not title or not title.strip():
        return False, "Название события не может быть пустым"
    if len(title.strip()) > 100:
        return False, "Название события слишком длинное (макс. 100 символов)"
    return True, ""


def validate_description(description: str) -> tuple[bool, str]:
    """Проверка описания события"""
    if description and len(description.strip()) > 500:
        return False, "Описание события слишком длинное (макс. 500 символов)"
    return True, ""


def validate_datetime(datetime_str: str) -> tuple[bool, str]:
    """Проверка даты и времени"""
    try:
        datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        return True, ""
    except ValueError:
        return False, "Неверный формат даты и времени! Используйте ГГГГ-ММ-ДД ЧЧ:ММ"


def validate_location(location: str) -> tuple[bool, str]:
    """Проверка места"""
    if location and len(location.strip()) > 100:
        return False, "Место слишком длинное (макс. 100 символов)"
    return True, ""


def save_event(user_id: int, data: dict) -> tuple[bool, int, str]:
    """Сохранение события в базу данных"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO events (user_id, title, description, event_datetime, location, is_recurring, recurrence_rule)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                data["title"],
                data.get("description"),
                data["event_datetime"],
                data.get("location"),
                data.get("is_recurring", False),
                data.get("recurrence_rule"),
            ),
        )
        conn.commit()
        event_id = cursor.lastrowid
        return True, event_id, "Событие успешно сохранено"

    except Exception as e:
        return False, 0, f"Ошибка при сохранении: {str(e)}"

    finally:
        conn.close()


def update_event(event_id: int, field: str, value) -> tuple[bool, str]:
    """Обновление поля события"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if field == "title":
            cursor.execute(
                "UPDATE events SET title = ? WHERE id = ?", (value, event_id)
            )
        elif field == "description":
            if value is None or (isinstance(value, str) and value.lower() == "нет"):
                value = None
            cursor.execute(
                "UPDATE events SET description = ? WHERE id = ?", (value, event_id)
            )
        elif field == "datetime":
            cursor.execute(
                "UPDATE events SET event_datetime = ? WHERE id = ?", (value, event_id)
            )
        elif field == "location":
            if value is None or (isinstance(value, str) and value.lower() == "нет"):
                value = None
            cursor.execute(
                "UPDATE events SET location = ? WHERE id = ?", (value, event_id)
            )
        elif field == "recurrence":
            is_recurring = value != "none"
            recurrence_rule = None if value == "none" else value
            cursor.execute(
                "UPDATE events SET is_recurring = ?, recurrence_rule = ? WHERE id = ?",
                (is_recurring, recurrence_rule, event_id),
            )

        conn.commit()
        return True, "Поле успешно обновлено"

    except Exception as e:
        return False, f"Ошибка при обновлении: {str(e)}"

    finally:
        conn.close()


def get_event(event_id: int):
    """Получение события по ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()
    conn.close()

    if event:
        return dict(event)
    return None


def get_user_events(user_id: int, upcoming_only=True):
    """Получение событий пользователя"""
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if upcoming_only:
        cursor.execute(
            """
            SELECT id, title, description, event_datetime, location, is_recurring, recurrence_rule
            FROM events
            WHERE user_id = ? AND event_datetime >= ?
            ORDER BY event_datetime
            """,
            (user_id, now),
        )
    else:
        cursor.execute(
            """
            SELECT id, title, description, event_datetime, location, is_recurring, recurrence_rule
            FROM events
            WHERE user_id = ?
            ORDER BY event_datetime DESC
            """,
            (user_id,),
        )

    events = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return events


def delete_event(event_id: int) -> bool:
    """Удаление события"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def format_event_details(event: dict) -> str:
    """Форматирование деталей события для отображения"""
    response = "🎯 <b>Детали события:</b>\n\n"
    response += f"📝 <b>Название:</b> {event['title']}\n"

    if event.get("description"):
        response += f"📄 <b>Описание:</b> {event['description']}\n"

    event_time = datetime.strptime(event["event_datetime"], "%Y-%m-%d %H:%M")
    formatted_time = event_time.strftime("%d.%m.%Y %H:%M")
    response += f"📅 <b>Дата и время:</b> {formatted_time}\n"

    if event.get("location"):
        response += f"📍 <b>Место:</b> {event['location']}\n"

    if event.get("is_recurring") and event.get("recurrence_rule"):
        recurrence_names = {
            "daily": "Ежедневно",
            "weekly": "Еженедельно",
            "monthly": "Ежемесячно",
            "yearly": "Ежегодно",
        }
        recurrence_text = recurrence_names.get(
            event["recurrence_rule"], event["recurrence_rule"]
        )
        response += f"🔄 <b>Повторяемость:</b> {recurrence_text}\n"

    return response
