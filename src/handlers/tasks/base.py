# src/handlers/tasks/base.py
"""Базовые функции для работы с задачами"""

import re
from datetime import datetime

from src.database import get_connection

# ==================== ВАЛИДАЦИЯ ====================

def validate_title(title: str) -> tuple[bool, str]:
    """Проверка названия задачи"""
    if not title or not title.strip():
        return False, "Название задачи не может быть пустым"
    if len(title.strip()) > 100:
        return False, "Название задачи слишком длинное (макс. 100 символов)"
    return True, ""


def validate_description(description: str) -> tuple[bool, str]:
    """Проверка описания задачи"""
    if description and len(description.strip()) > 500:
        return False, "Описание задачи слишком длинное (макс. 500 символов)"
    return True, ""


def validate_deadline(deadline: str) -> tuple[bool, str]:
    """Проверка дедлайна"""
    if not deadline or deadline.lower() == "нет":
        return True, ""

    try:
        datetime.strptime(deadline, "%Y-%m-%d")
        return True, ""
    except ValueError:
        return False, "Неверный формат даты! Используйте ГГГГ-ММ-ДД"


def validate_priority(priority: str) -> tuple[bool, str]:
    """Проверка приоритета"""
    valid_priorities = ["high", "medium", "low"]
    if priority not in valid_priorities:
        return False, "Неверный приоритет"
    return True, ""


# ==================== ОПЕРАЦИИ С БАЗОЙ ДАННЫХ ====================

def save_task(user_id: int, data: dict) -> tuple[bool, int, str]:
    """Сохранение задачи в базу данных"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO tasks (user_id, title, description, deadline, priority, is_completed)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                data["title"],
                data.get("description"),
                data.get("deadline"),
                data.get("priority", "medium"),
                False,
            ),
        )
        conn.commit()
        task_id = cursor.lastrowid
        return True, task_id, "Задача успешно сохранена"

    except Exception as e:
        return False, 0, f"Ошибка при сохранении: {str(e)}"

    finally:
        conn.close()


def update_task(task_id: int, field: str, value) -> tuple[bool, str]:
    """Обновление поля задачи"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if field == "title":
            cursor.execute("UPDATE tasks SET title = ? WHERE id = ?", (value, task_id))
        elif field == "description":
            if value is None or (isinstance(value, str) and value.lower() == "нет"):
                value = None
            cursor.execute(
                "UPDATE tasks SET description = ? WHERE id = ?", (value, task_id)
            )
        elif field == "deadline":
            if value is None or (isinstance(value, str) and value.lower() == "нет"):
                value = None
            cursor.execute(
                "UPDATE tasks SET deadline = ? WHERE id = ?", (value, task_id)
            )
        elif field == "priority":
            cursor.execute(
                "UPDATE tasks SET priority = ? WHERE id = ?", (value, task_id)
            )
        elif field == "complete":
            cursor.execute(
                "UPDATE tasks SET is_completed = ? WHERE id = ?", (value, task_id)
            )

        conn.commit()
        return True, "Поле успешно обновлено"

    except Exception as e:
        return False, f"Ошибка при обновлении: {str(e)}"

    finally:
        conn.close()


def get_task(task_id: int):
    """Получение задачи по ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    conn.close()

    if task:
        return dict(task)
    return None


def get_user_tasks(user_id: int, only_active=True):
    """Получение задач пользователя"""
    conn = get_connection()
    cursor = conn.cursor()

    if only_active:
        cursor.execute(
            """
            SELECT id, title, description, deadline, priority, is_completed
            FROM tasks
            WHERE user_id = ? AND is_completed = FALSE
            ORDER BY
                CASE priority
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4
                END,
                deadline
            """,
            (user_id,),
        )
    else:
        cursor.execute(
            """
            SELECT id, title, description, deadline, priority, is_completed
            FROM tasks
            WHERE user_id = ?
            ORDER BY is_completed, deadline
            """,
            (user_id,),
        )

    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks


def delete_task(task_id: int) -> bool:
    """Удаление задачи"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ==================== ФОРМАТИРОВАНИЕ ====================

def format_task_details(task: dict) -> str:
    """Форматирование деталей задачи для отображения"""
    response = "✅ <b>Детали задачи:</b>\n\n"
    response += f"📝 <b>Название:</b> {task['title']}\n"

    if task.get("description"):
        response += f"📄 <b>Описание:</b> {task['description']}\n"

    if task.get("deadline"):
        deadline_date = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
        today = datetime.now().date()

        if deadline_date < today:
            response += f"⏰ <b>Дедлайн:</b> {task['deadline']} <b>(ПРОСРОЧЕНО!)</b>\n"
        else:
            days_left = (deadline_date - today).days
            response += (
                f"📅 <b>Дедлайн:</b> {task['deadline']} (осталось {days_left} дней)\n"
            )

    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
        task.get("priority", "medium"), "⚪"
    )

    response += (
        f"🎯 <b>Приоритет:</b> {priority_emoji} {task.get('priority', 'medium')}\n"
    )
    response += f"📊 <b>Статус:</b> {'✅ Выполнена' if task.get('is_completed') else '⏳ В работе'}\n"

    return response


def format_task_preview(task: dict) -> str:
    """Форматирование краткой информации о задаче для списка"""
    title = task["title"][:25] + "..." if len(task["title"]) > 25 else task["title"]

    preview = f"📝 {title}"

    if task.get("deadline"):
        preview += f"\n📅 до: {task['deadline']}"

    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
        task.get("priority", "medium"), "⚪"
    )
    preview += f"\n{priority_emoji}"

    return preview


# ==================== УТИЛИТЫ ====================

def get_tasks_statistics(user_id: int) -> dict:
    """Получение статистики по задачам пользователя"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_completed = FALSE",
        (user_id,),
    )
    active_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_completed = TRUE",
        (user_id,),
    )
    completed_count = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*) FROM tasks
        WHERE user_id = ? AND deadline < date('now') AND is_completed = FALSE
        """,
        (user_id,),
    )
    overdue_count = cursor.fetchone()[0]

    conn.close()

    return {
        "active": active_count,
        "completed": completed_count,
        "overdue": overdue_count,
        "total": active_count + completed_count,
    }


def get_tasks_by_priority(user_id: int, priority: str):
    """Получение задач по приоритету"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, description, deadline, priority, is_completed
        FROM tasks
        WHERE user_id = ? AND priority = ? AND is_completed = FALSE
        ORDER BY deadline
        """,
        (user_id, priority),
    )

    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks


def get_upcoming_deadlines(user_id: int, days_ahead: int = 7):
    """Получение задач с ближайшими дедлайнами"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, description, deadline, priority, is_completed
        FROM tasks
        WHERE user_id = ?
          AND is_completed = FALSE
          AND deadline IS NOT NULL
          AND deadline BETWEEN date('now') AND date('now', ?)
        ORDER BY deadline
        """,
        (user_id, f"+{days_ahead} days"),
    )

    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks
