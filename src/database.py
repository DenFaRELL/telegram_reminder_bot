# src/database.py
import sqlite3
import os
from datetime import datetime

DB_NAME = "reminder_bot.db"

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        deadline DATE,
        is_completed BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT NOT NULL,
        event_date DATE NOT NULL,
        event_time TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        subject TEXT NOT NULL,
        day_of_week TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        room TEXT,
        teacher TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    print(f"База данных '{DB_NAME}' инициализирована")

def get_connection():
    return sqlite3.connect(DB_NAME)

def format_deadline(deadline_str):
    """Форматирование дедлайна"""
    if not deadline_str:
        return "без дедлайна"
    
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d")
        today = datetime.now().date()
        days_left = (deadline.date() - today).days
        
        if days_left < 0:
            return f"просрочено ({deadline_str})"
        elif days_left == 0:
            return "сегодня!"
        elif days_left == 1:
            return "завтра!"
        elif days_left < 7:
            return f"осталось {days_left} дня(ей)"
        else:
            return deadline_str
    except:
        return deadline_str