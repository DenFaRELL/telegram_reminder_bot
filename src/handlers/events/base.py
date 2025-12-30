# src/handlers/events/base.py
"""Базовые функции для работы с событиями"""

import re
from datetime import datetime

from src.database import get_connection


def validate_event_title(title: str) -> tuple[bool, str]:
    """Проверка названия события"""
    if not title or not title.strip():
        return False, "Название события не может быть пустым"
    if len(title.strip()) > 200:
        return False, "Название события слишком длинное (макс. 200 символов)"
    return True, ""


def validate_datetime(datetime_str: str) -> tuple[bool, str, datetime]:
    """Проверка даты и времени события"""
    if not datetime_str or not datetime_str.strip():
        return False, "Дата и время не могут быть пустыми", None

    try:
        # Пробуем разные форматы
        formats = ["%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%d/%m/%Y %H:%M"]

        event_datetime = None
        for fmt in formats:
            try:
                event_datetime = datetime.strptime(datetime_str, fmt)
                break
            except ValueError:
                continue

        if event_datetime is None:
            return False, "Неверный формат даты/времени. Используйте: ГГГГ-ММ-ДД ЧЧ:ММ (пример: 2024-12-31 18:30)", None

        # Проверяем, что дата не в прошлом
        if event_datetime < datetime.now():
            return False, "Дата и время события не могут быть в прошлом", None

        return True, "", event_datetime

    except Exception:
        return False, "Неверный формат даты/времени. Используйте: ГГГГ-ММ-ДД ЧЧ:ММ (пример: 2024-12-31 18:30)", None


def validate_location(location: str) -> tuple[bool, str]:
    """Проверка места проведения"""
    if not location or location.lower() == "нет":
        return True, ""

    if len(location.strip()) > 200:
        return False, "Название места слишком длинное (макс. 200 символов)"

    return True, ""


def validate_description(description: str) -> tuple[bool, str]:
    """Проверка описания события"""
    if not description or description.lower() == "нет":
        return True, ""

    if len(description.strip()) > 1000:
        return False, "Описание слишком длинное (макс. 1000 символов)"

    return True, ""


def validate_recurrence(recurrence: str) -> tuple[bool, str]:
    """Проверка правила повторяемости"""
    valid_recurrences = ["none", "daily", "weekly", "monthly", "yearly"]
    if recurrence not in valid_recurrences:
        return False, f"Неверное правило повторяемости. Доступные: {', '.join(valid_recurrences)}"
    return True, ""


def save_event(user_id: int, data: dict) -> tuple[bool, int, str]:
    """Сохранение события в базу данных"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Преобразуем datetime в строку для базы данных
        event_datetime_str = data["event_datetime"].strftime("%Y-%m-%d %H:%M") if isinstance(data["event_datetime"], datetime) else data["event_datetime"]

        cursor.execute(
            """
            INSERT INTO events (user_id, title, description, event_datetime, location, is_recurring, recurrence_rule)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                data["title"],
                data.get("description", None),
                event_datetime_str,
                data.get("location", None),
                data.get("is_recurring", False),
                data.get("recurrence_rule", None),
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
        # Для пустых значений ставим None
        if value is None or (isinstance(value, str) and value.lower() == "нет"):
            value = None

        # Для datetime преобразуем в строку
        if field == "event_datetime" and isinstance(value, datetime):
            value = value.strftime("%Y-%m-%d %H:%M")

        if field == "title":
            cursor.execute(
                "UPDATE events SET title = ? WHERE id = ?", (value, event_id)
            )
        elif field == "description":
            cursor.execute(
                "UPDATE events SET description = ? WHERE id = ?", (value, event_id)
            )
        elif field == "event_datetime":
            cursor.execute(
                "UPDATE events SET event_datetime = ? WHERE id = ?", (value, event_id)
            )
        elif field == "location":
            cursor.execute(
                "UPDATE events SET location = ? WHERE id = ?", (value, event_id)
            )
        elif field == "recurrence_rule":
            # Обновляем оба поля: recurrence_rule и is_recurring
            is_recurring = value != "none"
            cursor.execute(
                "UPDATE events SET recurrence_rule = ?, is_recurring = ? WHERE id = ?",
                (value if value != "none" else None, is_recurring, event_id)
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


def get_user_events(user_id: int):
    """Получение событий пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, title, event_datetime, location, description, is_recurring, recurrence_rule
        FROM events
        WHERE user_id = ?
        ORDER BY event_datetime
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

    # Форматируем дату и время
    if event.get('event_datetime'):
        try:
            event_dt = datetime.strptime(event['event_datetime'], "%Y-%m-%d %H:%M")
            response += f"📅 <b>Дата и время:</b> {event_dt.strftime('%d.%m.%Y %H:%M')}\n"
        except:
            response += f"📅 <b>Дата и время:</b> {event['event_datetime']}\n"

    if event.get('location'):
        response += f"📍 <b>Место:</b> {event['location']}\n"

    if event.get('description'):
        response += f"📄 <b>Описание:</b> {event['description']}\n"

    # Информация о повторяемости
    if event.get('is_recurring') and event.get('recurrence_rule'):
        recurrence_text = {
            "daily": "Ежедневно",
            "weekly": "Еженедельно",
            "monthly": "Ежемесячно",
            "yearly": "Ежегодно"
        }.get(event['recurrence_rule'], event['recurrence_rule'])
        response += f"🔄 <b>Повторяемость:</b> {recurrence_text}\n"

    return response
