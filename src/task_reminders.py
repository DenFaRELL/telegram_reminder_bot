# src/task_reminders.py
"""Модуль напоминаний о задачах (дедлайнах)"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from aiogram import Bot

from src.database import get_connection

logger = logging.getLogger(__name__)


class TaskReminderService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running = False
        self.reminder_schedule = [7, 3, 1, 0.5]  # Дни до дедлайна

    async def start(self):
        """Запуск сервиса напоминаний о задачах"""
        self.running = True
        logger.info("🚀 Сервис напоминаний о задачах запущен")

        while self.running:
            try:
                await self.check_upcoming_deadlines()
                await self.send_scheduled_reminders()
                await asyncio.sleep(60)  # Проверяем каждую минуту
            except Exception as e:
                logger.error(f"Ошибка в сервисе напоминаний о задачах: {e}")
                await asyncio.sleep(60)

    async def stop(self):
        """Остановка сервиса"""
        self.running = False
        logger.info("🛑 Сервис напоминаний о задачах остановлен")

    async def check_upcoming_deadlines(self):
        """Проверка предстоящих дедлайнов и создание напоминаний"""
        conn = get_connection()
        cursor = conn.cursor()

        now = datetime.now()

        # Ищем задачи с дедлайнами в ближайшие 14 дней
        deadline_threshold = now + timedelta(days=14)

        cursor.execute(
            """
            SELECT t.*, u.telegram_id, u.username
            FROM tasks t
            JOIN users u ON t.user_id = u.telegram_id
            WHERE t.deadline BETWEEN ? AND ?
            AND t.is_completed = 0
            AND t.deadline IS NOT NULL
            AND (t.last_reminder_sent IS NULL OR t.last_reminder_sent < ?)
            """,
            (
                now.strftime("%Y-%m-%d"),
                deadline_threshold.strftime("%Y-%m-%d"),
                (now - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M"),  # Не отправлять чаще чем раз в 12 часов
            ),
        )

        tasks = cursor.fetchall()
        conn.close()

        for task in tasks:
            await self.schedule_task_reminders(task)

    async def schedule_task_reminders(self, task):
        """Создание напоминаний для задачи"""
        try:
            deadline_date = datetime.strptime(task["deadline"], "%Y-%m-%d")
            now = datetime.now()

            # Пропускаем просроченные задачи
            if deadline_date.date() < now.date():
                return

            # Для каждого времени в расписании создаем напоминание
            for days_before in self.reminder_schedule:
                reminder_time = deadline_date - timedelta(days=days_before)

                # Если время напоминания еще не наступило и не в прошлом
                if now < reminder_time < deadline_date:
                    reminder_type = f"{days_before}d"
                    await self.create_reminder(task["id"], reminder_time, reminder_type)

            # Обновляем время последнего напоминания
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET last_reminder_sent = ? WHERE id = ?",
                (now.strftime("%Y-%m-%d %H:%M"), task["id"])
            )
            conn.commit()
            conn.close()

            logger.info(f"Созданы напоминания для задачи {task['id']}: {task['title']}")

        except Exception as e:
            logger.error(f"Ошибка при создании напоминаний для задачи {task['id']}: {e}")

    async def create_reminder(self, task_id: int, reminder_time: datetime, reminder_type: str):
        """Создание записи о напоминании в БД"""
        conn = get_connection()
        cursor = conn.cursor()

        # Проверяем, не существует ли уже такое напоминание
        cursor.execute(
            """
            SELECT id FROM task_reminders
            WHERE task_id = ? AND reminder_type = ? AND reminder_sent = 0
            """,
            (task_id, reminder_type)
        )

        existing = cursor.fetchone()

        if not existing:
            cursor.execute(
                """
                INSERT INTO task_reminders (task_id, reminder_type, reminder_time)
                VALUES (?, ?, ?)
                """,
                (
                    task_id,
                    reminder_type,
                    reminder_time.strftime("%Y-%m-%d %H:%M"),
                ),
            )
            conn.commit()

        conn.close()

    async def send_scheduled_reminders(self):
        """Отправка запланированных напоминаний о задачах"""
        conn = get_connection()
        cursor = conn.cursor()

        now = datetime.now()
        future_threshold = now + timedelta(minutes=10)  # +10 минут для компенсации задержек

        cursor.execute(
            """
            SELECT r.*, t.title, t.deadline, t.description, t.priority,
                   u.telegram_id, u.username
            FROM task_reminders r
            JOIN tasks t ON r.task_id = t.id
            JOIN users u ON t.user_id = u.telegram_id
            WHERE r.reminder_sent = 0
            AND r.reminder_time BETWEEN ? AND ?
            AND t.is_completed = 0
            """,
            (
                now.strftime("%Y-%m-%d %H:%M"),
                future_threshold.strftime("%Y-%m-%d %H:%M"),
            ),
        )

        reminders = cursor.fetchall()

        for reminder in reminders:
            try:
                await self.send_task_reminder(reminder)

                # Помечаем напоминание как отправленное
                cursor.execute(
                    "UPDATE task_reminders SET reminder_sent = 1 WHERE id = ?",
                    (reminder["id"],)
                )
                conn.commit()

            except Exception as e:
                logger.error(f"Ошибка при отправке напоминания о задаче {reminder['id']}: {e}")

        conn.close()

    async def send_task_reminder(self, reminder):
        """Отправка конкретного напоминания о задаче"""
        try:
            deadline_date = datetime.strptime(reminder["deadline"], "%Y-%m-%d")
            now = datetime.now()

            # Вычисляем оставшееся время
            time_left = deadline_date.date() - now.date()
            days_left = time_left.days

            # Форматируем дату дедлайна
            formatted_date = deadline_date.strftime("%d.%m.%Y")

            # Определяем текст в зависимости от времени до дедлайна
            reminder_type = reminder["reminder_type"]
            time_text = self.get_time_text(reminder_type, days_left)

            # Эмодзи приоритета
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                reminder.get("priority", "medium"), "⚪"
            )

            # Создаем сообщение
            message = f"⏰ <b>Напоминание о задаче!</b>\n\n"
            message += f"📝 <b>{reminder['title']}</b>\n"
            message += f"📅 <b>Дедлайн:</b> {formatted_date}\n"
            message += f"{priority_emoji} <b>Приоритет:</b> {reminder.get('priority', 'medium')}\n"

            if reminder["description"]:
                desc = reminder["description"]
                if len(desc) > 100:
                    desc = desc[:100] + "..."
                message += f"📄 <b>Описание:</b> {desc}\n"

            message += f"\n⏳ <b>До дедлайна осталось:</b> {time_text}"

            # Добавляем эмодзи в зависимости от срочности
            if days_left <= 1:
                message += " 🚨"
            elif days_left <= 3:
                message += " ⚠️"

            # Отправляем сообщение
            await self.bot.send_message(
                chat_id=reminder["telegram_id"],
                text=message,
                parse_mode="HTML"
            )

            logger.info(f"Отправлено напоминание о задаче {reminder['task_id']} пользователю {reminder['telegram_id']}")

        except Exception as e:
            logger.error(f"Ошибка при формировании напоминания о задаче: {e}")
            raise

    def get_time_text(self, reminder_type: str, days_left: int) -> str:
        """Получить текстовое представление оставшегося времени"""
        if reminder_type == "0.5d":
            hours_left = days_left * 24
            if hours_left <= 12:
                return "менее 12 часов"
            return "менее дня"
        elif reminder_type == "1d":
            if days_left == 0:
                return "менее 24 часов"
            return "1 день"
        elif reminder_type == "3d":
            return f"{days_left} дня" if days_left <= 3 else "3 дня"
        elif reminder_type == "7d":
            return f"{days_left} дней" if days_left <= 7 else "7 дней"
        else:
            return f"{days_left} дней"

    async def cleanup_old_reminders(self):
        """Очистка старых напоминаний о задачах"""
        conn = get_connection()
        cursor = conn.cursor()

        week_ago = datetime.now() - timedelta(days=7)

        cursor.execute(
            "DELETE FROM task_reminders WHERE reminder_time < ?",
            (week_ago.strftime("%Y-%m-%d %H:%M"),)
        )

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted_count > 0:
            logger.info(f"Удалено {deleted_count} старых напоминаний о задачах")


# Синглтон экземпляр
_task_reminder_service = None


def get_task_reminder_service(bot: Bot = None) -> TaskReminderService:
    """Получить экземпляр сервиса напоминаний о задачах"""
    global _task_reminder_service
    if _task_reminder_service is None and bot is not None:
        _task_reminder_service = TaskReminderService(bot)
    return _task_reminder_service
