# src/database.py
import os
import sqlite3
from datetime import datetime


def get_connection():
    """Создает соединение с базой данных"""
    db_path = os.path.join(os.path.dirname(__file__), "..", "bot.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Включаем foreign keys
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def init_database():
    """Инициализация базы данных (создание таблиц)"""
    conn = get_connection()
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Таблица расписания
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            day_of_week TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            build TEXT,
            room TEXT,
            teacher TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
        )
    """
    )

    # Таблица задач
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            deadline DATE,
            priority TEXT CHECK(priority IN ('high', 'medium', 'low')),
            is_completed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
        )
    """
    )

    # Таблица событий
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            event_datetime DATETIME NOT NULL,
            location TEXT,
            is_recurring BOOLEAN DEFAULT 0,
            recurrence_rule TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
        )
    """
    )

    # Таблица для напоминаний о событиях
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS event_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            reminder_type TEXT NOT NULL,
            reminder_time DATETIME NOT NULL,
            reminder_sent BOOLEAN DEFAULT 0,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        )
    """
    )

    # Таблица для напоминаний о задачах
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS task_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            reminder_type TEXT NOT NULL,
            reminder_time DATETIME NOT NULL,
            reminder_sent BOOLEAN DEFAULT 0,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
    """
    )

    # Добавляем поля для отслеживания напоминаний, если их нет
    cursor.execute("PRAGMA table_info(events)")
    events_columns = [col[1] for col in cursor.fetchall()]
    if "last_reminder_sent" not in events_columns:
        cursor.execute("ALTER TABLE events ADD COLUMN last_reminder_sent DATETIME")

    cursor.execute("PRAGMA table_info(tasks)")
    tasks_columns = [col[1] for col in cursor.fetchall()]
    if "last_reminder_sent" not in tasks_columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN last_reminder_sent DATETIME")

    # Создаем индексы для ускорения запросов
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_schedule_user_id ON schedule(user_id)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_datetime ON events(event_datetime)"
    )

    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")


def fix_invalid_dates():
    """Исправление неверных дат в базе данных"""
    conn = get_connection()
    cursor = conn.cursor()

    # Находим задачи с некорректными датами
    cursor.execute("SELECT id, deadline FROM tasks WHERE deadline IS NOT NULL")
    tasks = cursor.fetchall()

    fixed_count = 0
    for task in tasks:
        task_id = task["id"]
        deadline = task["deadline"]

        try:
            # Пробуем преобразовать дату
            datetime.strptime(deadline, "%Y-%m-%d")
        except (ValueError, TypeError):
            # Если дата некорректная, удаляем её
            print(f"Исправление некорректной даты в задаче {task_id}: {deadline}")
            cursor.execute("UPDATE tasks SET deadline = NULL WHERE id = ?", (task_id,))
            fixed_count += 1

    conn.commit()
    conn.close()
    print(f"✅ Некорректные даты исправлены. Исправлено записей: {fixed_count}")


if __name__ == "__main__":
    init_database()
    fix_invalid_dates()
