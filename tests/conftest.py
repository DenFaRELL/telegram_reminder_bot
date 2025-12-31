import os
import sqlite3
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def test_db():
    """Фикстура для тестовой базы данных"""
    # Создаем временный файл БД
    db_fd, db_path = tempfile.mkstemp()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # SQL для создания таблиц
    sql_script = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        notification_time TEXT DEFAULT '09:00',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        day_of_week TEXT NOT NULL,
        start_time TEXT,
        end_time TEXT,
        classroom TEXT,
        teacher TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        priority TEXT DEFAULT 'medium',
        deadline DATE,
        is_completed INTEGER DEFAULT 0,
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        event_datetime TIMESTAMP NOT NULL,
        is_recurring INTEGER DEFAULT 0,
        recurrence_rule TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    INSERT OR IGNORE INTO users (id, telegram_id, username)
    VALUES (1, 123456, 'test_user');
    """

    conn.executescript(sql_script)
    conn.commit()

    yield conn

    # Закрываем соединение и удаляем файл
    conn.close()
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def message():
    """Фикстура для имитации сообщения"""
    mock_message = MagicMock()
    mock_message.answer = AsyncMock()
    mock_message.delete = AsyncMock()
    mock_message.from_user = MagicMock()
    mock_message.from_user.id = 123456
    mock_message.from_user.username = "test_user"
    mock_message.chat = MagicMock()
    mock_message.chat.id = 123456
    mock_message.text = "/start"
    mock_message.message_id = 1
    return mock_message


@pytest.fixture
def callback():
    """Фикстура для имитации callback запроса"""
    mock_callback = MagicMock()
    mock_callback.data = "test"
    mock_callback.message = MagicMock()
    mock_callback.message.answer = AsyncMock()
    mock_callback.message.delete = AsyncMock()
    mock_callback.message.chat = MagicMock()
    mock_callback.message.chat.id = 123456
    mock_callback.message.message_id = 1
    mock_callback.from_user = MagicMock()
    mock_callback.from_user.id = 123456
    mock_callback.from_user.username = "test_user"
    mock_callback.answer = AsyncMock()
    return mock_callback


@pytest.fixture
def state():
    """Фикстура для имитации состояния FSM"""
    mock_state = MagicMock()
    mock_state.set_state = AsyncMock()
    mock_state.get_state = AsyncMock()
    mock_state.finish = AsyncMock()
    mock_state.update_data = AsyncMock()
    return mock_state
