# src/handlers/tasks/base.py
"""Базовые функции для работы с задачами"""

import logging
from datetime import datetime

from src.database import get_connection

logger = logging.getLogger(__name__)


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

    # Нормализуем для проверки
    normalized = normalize_date_for_db(deadline)

    try:
        # Теперь проверяем нормализованную дату
        datetime.strptime(normalized, "%Y-%m-%d")
        return True, ""
    except ValueError:
        return (
            False,
            "Неверный формат даты! Используйте ГГГГ-ММ-ДД, ДД.ММ.ГГГГ или ДД/ММ/ГГГГ",
        )


def validate_priority(priority: str) -> tuple[bool, str]:
    """Проверка приоритета"""
    valid_priorities = ["high", "medium", "low"]
    if priority not in valid_priorities:
        return False, "Неверный приоритет"
    return True, ""


# ==================== ОПЕРАЦИИ С БАЗОЙ ДАННЫХ ====================


def normalize_date_for_db(date_str: str):
    """Нормализует дату для сохранения в БД: из любого формата в ГГГГ-ММ-ДД"""
    if not date_str or date_str.lower() == "нет":
        return None

    try:
        # Пробуем разные форматы
        for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime("%Y-%m-%d")  # Всегда возвращаем ГГГГ-ММ-ДД
            except ValueError:
                continue

        # Если не распарсилось, пробуем разобрать вручную
        parts = date_str.split("-")
        if len(parts) == 3:
            year = parts[0]
            month = parts[1].zfill(2)  # Добавляем ведущий ноль
            day = parts[2].zfill(2)  # Добавляем ведущий ноль
            return f"{year}-{month}-{day}"

        # Если всё плохо - возвращаем как есть (будет ошибка при валидации)
        return date_str
    except Exception:
        return date_str


def save_task(user_id: int, data: dict) -> tuple[bool, int, str]:
    """Сохранение задачи в базу данных"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        deadline = data.get("deadline")

        # НОРМАЛИЗУЕМ дату перед сохранением
        if deadline:
            deadline = normalize_date_for_db(deadline)

        cursor.execute(
            """
            INSERT INTO tasks (user_id, title, description, deadline, priority, is_completed)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                data["title"],
                data.get("description"),
                deadline,
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
            else:
                # НОРМАЛИЗУЕМ дату перед сохранением
                value = normalize_date_for_db(value)
            cursor.execute(
                "UPDATE tasks SET deadline = ? WHERE id = ?", (value, task_id)
            )
        elif field == "priority":
            cursor.execute(
                "UPDATE tasks SET priority = ? WHERE id = ?", (value, task_id)
            )
        elif field == "complete":
            # SQLite использует 1 для True, 0 для False
            is_completed = 1 if value else 0
            cursor.execute(
                "UPDATE tasks SET is_completed = ? WHERE id = ?",
                (is_completed, task_id),
            )
        else:
            return False, f"Неизвестное поле: {field}"

        conn.commit()
        rows_affected = cursor.rowcount
        logger.info(
            f"Обновлена задача {task_id}, поле '{field}', затронуто строк: {rows_affected}"
        )

        return True, "Поле успешно обновлено"

    except Exception as e:
        logger.error(f"Ошибка при обновлении задачи {task_id}, поле {field}: {e}")
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
            WHERE user_id = ? AND is_completed = 0
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
            SELECT id, title, description, deadline, priority, is_completed, created_at
            FROM tasks
            WHERE user_id = ?
            ORDER BY
                is_completed,  -- Сначала активные
                CASE WHEN is_completed = 0 THEN
                    CASE priority
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                        ELSE 4
                    END
                ELSE 0 END,
                CASE WHEN is_completed = 0 THEN deadline ELSE created_at END,
                id DESC  -- Новые задачи первыми
            """,
            (user_id,),
        )

    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()

    logger.info(
        f"Загружено задач для пользователя {user_id}: {len(tasks)} (only_active={only_active})"
    )
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
        # Форматируем дату из ГГГГ-ММ-ДД в ДД.ММ.ГГГГ
        try:
            deadline_date = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
            formatted_deadline = deadline_date.strftime("%d.%m.%Y")
            today = datetime.now().date()

            if deadline_date < today:
                response += (
                    f"⏰ <b>Дедлайн:</b> {formatted_deadline} <b>(ПРОСРОЧЕНО!)</b>\n"
                )
            else:
                days_left = (deadline_date - today).days
                response += f"📅 <b>Дедлайн:</b> {formatted_deadline} (осталось {days_left} дней)\n"
        except:
            # Если не удалось распарсить, показываем как есть
            response += f"📅 <b>Дедлайн:</b> {task['deadline']}\n"

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
