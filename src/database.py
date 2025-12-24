import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "bot.db"):
        self.db_path = db_path
        self.connection = None
        self._init_db()
    
    def _init_db(self):
        """Инициализация базы данных и создание таблиц"""
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        cursor = self.connection.cursor()
        
        # Таблица пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица расписания
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
                start_time TEXT NOT NULL,  -- HH:MM
                end_time TEXT NOT NULL,    -- HH:MM
                subject_name TEXT NOT NULL,
                subject_type TEXT CHECK(subject_type IN ('lecture', 'practice', 'lab', 'other')),
                is_active BOOLEAN DEFAULT 1,
                room_number TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Таблица задач
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                deadline TIMESTAMP,
                priority TEXT CHECK(priority IN ('high', 'medium', 'low')) DEFAULT 'medium',
                is_completed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Таблица событий
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                event_date TIMESTAMP NOT NULL,
                reminder_before INTEGER DEFAULT 24,  -- часы до события
                is_recurring BOOLEAN DEFAULT 0,
                recurrence_pattern TEXT,  -- daily/weekly/monthly
                next_reminder_time TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Индексы для быстрого поиска
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_deadline ON tasks(user_id, deadline, is_completed)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_reminder ON events(next_reminder_time)")
        
        self.connection.commit()
        logger.info("База данных инициализирована")
    
    # Методы для работы с пользователями
    def add_user(self, telegram_id: int, username: Optional[str], full_name: str) -> int:
        """Добавление нового пользователя"""
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username, full_name) VALUES (?, ?, ?)",
            (telegram_id, username, full_name)
        )
        self.connection.commit()
        return cursor.lastrowid
    
    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по telegram_id"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # Методы для расписания
    def add_schedule_item(self, user_id: int, day_of_week: int, start_time: str, 
                         end_time: str, subject_name: str, subject_type: str = "lecture", 
                         room_number: str = "") -> int:
        """Добавление пары в расписание"""
        cursor = self.connection.cursor()
        cursor.execute(
            """INSERT INTO schedule 
            (user_id, day_of_week, start_time, end_time, subject_name, subject_type, room_number)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, day_of_week, start_time, end_time, subject_name, subject_type, room_number)
        )
        self.connection.commit()
        return cursor.lastrowid
    
    def get_user_schedule(self, user_id: int, day_of_week: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получение расписания пользователя"""
        cursor = self.connection.cursor()
        if day_of_week is not None:
            cursor.execute(
                "SELECT * FROM schedule WHERE user_id = ? AND day_of_week = ? AND is_active = 1 ORDER BY start_time",
                (user_id, day_of_week)
            )
        else:
            cursor.execute(
                "SELECT * FROM schedule WHERE user_id = ? AND is_active = 1 ORDER BY day_of_week, start_time",
                (user_id,)
            )
        return [dict(row) for row in cursor.fetchall()]
    
    # Методы для задач
    def add_task(self, user_id: int, title: str, description: str = "", 
                 deadline: Optional[datetime] = None, priority: str = "medium") -> int:
        """Добавление задачи"""
        cursor = self.connection.cursor()
        cursor.execute(
            """INSERT INTO tasks 
            (user_id, title, description, deadline, priority)
            VALUES (?, ?, ?, ?, ?)""",
            (user_id, title, description, deadline, priority)
        )
        self.connection.commit()
        return cursor.lastrowid
    
    def get_user_tasks(self, user_id: int, completed: bool = False, upcoming: bool = True) -> List[Dict[str, Any]]:
        """Получение задач пользователя"""
        cursor = self.connection.cursor()
        query = "SELECT * FROM tasks WHERE user_id = ? AND is_completed = ?"
        params = [user_id, 1 if completed else 0]
        
        if upcoming:
            query += " AND (deadline IS NULL OR deadline > datetime('now'))"
        
        query += " ORDER BY deadline ASC NULLS LAST"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # Методы для событий
    def add_event(self, user_id: int, title: str, event_date: datetime, 
                  description: str = "", reminder_before: int = 24,
                  is_recurring: bool = False, recurrence_pattern: str = None) -> int:
        """Добавление события"""
        cursor = self.connection.cursor()
        cursor.execute(
            """INSERT INTO events 
            (user_id, title, description, event_date, reminder_before, is_recurring, recurrence_pattern, next_reminder_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, title, description, event_date, reminder_before, 
             is_recurring, recurrence_pattern, event_date)  # начальное напоминание = время события
        )
        self.connection.commit()
        return cursor.lastrowid
    
    def get_upcoming_events(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение ближайших событий"""
        cursor = self.connection.cursor()
        cursor.execute(
            """SELECT * FROM events 
            WHERE user_id = ? AND event_date > datetime('now')
            ORDER BY event_date ASC
            LIMIT ?""",
            (user_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Закрытие соединения с БД"""
        if self.connection:
            self.connection.close()