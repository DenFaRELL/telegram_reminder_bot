# src/event_reminders.py
"""Модуль напоминаний о событиях"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from aiogram import Bot

from src.database import get_connection

logger = logging.getLogger(__name__)


class EventReminderService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running = False
        self.reminder_schedule = [24, 12, 6, 3, 1, 0.5]  # Часы до события

    async def start(self):
        """Запуск сервиса напоминаний"""
        self.running = True
        logger.info("🚀 Сервис напоминаний о событиях запущен")

        while self.running:
            try:
                await self.check_upcoming_events()
                await self.send_scheduled_reminders()
                await asyncio.sleep(30)  # Проверяем каждые 30 секунд
            except Exception as e:
                logger.error(f"Ошибка в сервисе напоминаний: {e}")
                await asyncio.sleep(60)

    async def stop(self):
        """Остановка сервиса"""
        self.running = False
        logger.info("🛑 Сервис напоминаний о событиях остановлен")

    async def check_upcoming_events(self):
        """Проверка предстоящих событий и создание напоминаний"""
        conn = get_connection()
        cursor = conn.cursor()

        now = datetime.now()

        # Ищем события в ближайшие 48 часов
        time_threshold = now + timedelta(hours=48)

        cursor.execute(
            """
            SELECT e.*, u.telegram_id, u.username
            FROM events e
            JOIN users u ON e.user_id = u.telegram_id
            WHERE e.event_datetime BETWEEN ? AND ?
            AND (e.last_reminder_sent IS NULL OR e.last_reminder_sent < ?)
            """,
            (
                now.strftime("%Y-%m-%d %H:%M"),
                time_threshold.strftime("%Y-%m-%d %H:%M"),
                (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"),  # Не отправлять чаще чем раз в час
            ),
        )

        events = cursor.fetchall()
        conn.close()

        for event in events:
            await self.schedule_event_reminders(event)

    async def schedule_event_reminders(self, event):
        """Создание напоминаний для события"""
        try:
            event_time = datetime.strptime(event["event_datetime"], "%Y-%m-%d %H:%M")
            now = datetime.now()

            # Пропускаем события в прошлом
            if event_time <= now:
                return

            # Для каждого времени в расписании создаем напоминание
            for hours_before in self.reminder_schedule:
                reminder_time = event_time - timedelta(hours=hours_before)

                # Если время напоминания еще не наступило и не в прошлом
                if now < reminder_time < event_time:
                    await self.create_reminder(event["id"], reminder_time, f"{hours_before}h")

            # Обновляем время последнего напоминания
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE events SET last_reminder_sent = ? WHERE id = ?",
                (now.strftime("%Y-%m-%d %H:%M"), event["id"])
            )
            conn.commit()
            conn.close()

            logger.info(f"Созданы напоминания для события {event['id']}: {event['title']}")

        except Exception as e:
            logger.error(f"Ошибка при создании напоминаний для события {event['id']}: {e}")

    async def create_reminder(self, event_id: int, reminder_time: datetime, reminder_type: str):
        """Создание записи о напоминании в БД"""
        conn = get_connection()
        cursor = conn.cursor()

        # Проверяем, не существует ли уже такое напоминание
        cursor.execute(
            """
            SELECT id FROM reminders
            WHERE event_id = ? AND reminder_type = ? AND reminder_sent = 0
            """,
            (event_id, reminder_type)
        )

        existing = cursor.fetchone()

        if not existing:
            cursor.execute(
                """
                INSERT INTO reminders (event_id, reminder_type, reminder_time)
                VALUES (?, ?, ?)
                """,
                (
                    event_id,
                    reminder_type,
                    reminder_time.strftime("%Y-%m-%d %H:%M"),
                ),
            )
            conn.commit()

        conn.close()

    async def send_scheduled_reminders(self):
        """Отправка запланированных напоминаний"""
        conn = get_connection()
        cursor = conn.cursor()

        now = datetime.now()
        future_threshold = now + timedelta(minutes=5)  # +5 минут для компенсации задержек

        cursor.execute(
            """
            SELECT r.*, e.title, e.event_datetime, e.location, e.description,
                   u.telegram_id, u.username
            FROM reminders r
            JOIN events e ON r.event_id = e.id
            JOIN users u ON e.user_id = u.telegram_id
            WHERE r.reminder_sent = 0
            AND r.reminder_time BETWEEN ? AND ?
            """,
            (
                now.strftime("%Y-%m-%d %H:%M"),
                future_threshold.strftime("%Y-%m-%d %H:%M"),
            ),
        )

        reminders = cursor.fetchall()

        for reminder in reminders:
            try:
                await self.send_reminder(reminder)

                # Помечаем напоминание как отправленное
                cursor.execute(
                    "UPDATE reminders SET reminder_sent = 1 WHERE id = ?",
                    (reminder["id"],)
                )
                conn.commit()

            except Exception as e:
                logger.error(f"Ошибка при отправке напоминания {reminder['id']}: {e}")

        conn.close()

    async def send_reminder(self, reminder):
        """Отправка конкретного напоминания"""
        try:
            event_time = datetime.strptime(reminder["event_datetime"], "%Y-%m-%d %H:%M")
            now = datetime.now()

            # Вычисляем оставшееся время
            time_left = event_time - now

            # Форматируем время события
            formatted_time = event_time.strftime("%d.%m.%Y в %H:%M")

            # Определяем текст в зависимости от времени до события
            reminder_type = reminder["reminder_type"]
            time_text = self.get_time_text(reminder_type, time_left)

            # Создаем сообщение
            message = f"🔔 <b>Напоминание о событии!</b>\n\n"
            message += f"📝 <b>{reminder['title']}</b>\n"
            message += f"📅 <b>Когда:</b> {formatted_time}\n"

            if reminder["location"]:
                message += f"📍 <b>Где:</b> {reminder['location']}\n"

            if reminder["description"]:
                desc = reminder["description"]
                if len(desc) > 100:
                    desc = desc[:100] + "..."
                message += f"📄 <b>Описание:</b> {desc}\n"

            message += f"\n⏰ <b>До события осталось:</b> {time_text}"

            # Добавляем эмодзи в зависимости от срочности
            if "0.5h" in reminder_type or "1h" in reminder_type:
                message += " 🚨"
            elif "3h" in reminder_type or "6h" in reminder_type:
                message += " ⚠️"

            # Отправляем сообщение
            await self.bot.send_message(
                chat_id=reminder["telegram_id"],
                text=message,
                parse_mode="HTML"
            )

            logger.info(f"Отправлено напоминание пользователю {reminder['telegram_id']} о событии {reminder['title']}")

        except Exception as e:
            logger.error(f"Ошибка при формировании напоминания: {e}")
            raise

    def get_time_text(self, reminder_type: str, time_left: timedelta) -> str:
        """Получить текстовое представление оставшегося времени"""
        if reminder_type == "0.5h":
            minutes = int(time_left.total_seconds() / 60)
            return f"{minutes} минут"
        elif reminder_type == "1h":
            hours = int(time_left.total_seconds() / 3600)
            minutes = int((time_left.total_seconds() % 3600) / 60)
            if minutes > 0:
                return f"{hours} ч {minutes} мин"
            return f"{hours} час"
        else:
            # Для других типов показываем в часах
            hours = int(time_left.total_seconds() / 3600)
            return f"{hours} часов"

    async def cleanup_old_reminders(self):
        """Очистка старых напоминаний"""
        conn = get_connection()
        cursor = conn.cursor()

        week_ago = datetime.now() - timedelta(days=7)

        cursor.execute(
            "DELETE FROM reminders WHERE reminder_time < ?",
            (week_ago.strftime("%Y-%m-%d %H:%M"),)
        )

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted_count > 0:
            logger.info(f"Удалено {deleted_count} старых напоминаний")


# Синглтон экземпляр
_event_reminder_service = None


def get_event_reminder_service(bot: Bot = None) -> EventReminderService:
    """Получить экземпляр сервиса напоминаний о событиях"""
    global _event_reminder_service
    if _event_reminder_service is None and bot is not None:
        _event_reminder_service = EventReminderService(bot)
    return _event_reminder_service
