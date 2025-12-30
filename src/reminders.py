# src/reminders.py
"""Модуль напоминаний"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List

from aiogram import Bot

from src.database import get_connection


class ReminderService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running = False

    async def start(self):
        """Запуск сервиса напоминаний"""
        self.running = True
        while self.running:
            await self.check_reminders()
            await asyncio.sleep(60)  # Проверяем каждую минуту

    async def stop(self):
        """Остановка сервиса"""
        self.running = False

    async def check_reminders(self):
        """Проверка и отправка напоминаний"""
        try:
            # Проверяем события
            await self.check_events_reminders()
            # Проверяем задачи с дедлайнами
            await self.check_tasks_deadlines()
        except Exception as e:
            print(f"Ошибка в check_reminders: {e}")

    async def check_events_reminders(self):
        """Проверка напоминаний о событиях"""
        conn = get_connection()
        cursor = conn.cursor()

        now = datetime.now()

        # События в ближайшие 24 часа
        cursor.execute(
            """
            SELECT e.*, u.telegram_id
            FROM events e
            JOIN users u ON e.user_id = u.telegram_id
            WHERE e.event_datetime BETWEEN ? AND ?
            AND e.event_datetime > ?
        """,
            (
                now.strftime("%Y-%m-%d %H:%M"),
                (now + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M"),
                now.strftime("%Y-%m-%d %H:%M"),
            ),
        )

        events = cursor.fetchall()
        conn.close()

        for event in events:
            event_time = datetime.strptime(event["event_datetime"], "%Y-%m-%d %H:%M")
            time_diff = event_time - now

            # Определяем когда отправлять напоминание
            reminder_sent = False
            reminder_hours = [24, 12, 6, 3, 1]  # За сколько часов напоминать

            for hours in reminder_hours:
                if timedelta(hours=hours) >= time_diff > timedelta(hours=hours - 1):
                    await self.send_event_reminder(event)
                    reminder_sent = True
                    break

            # Если событие через 30 минут или меньше
            if not reminder_sent and time_diff <= timedelta(minutes=30):
                await self.send_event_reminder(event)

    async def check_tasks_deadlines(self):
        """Проверка дедлайнов задач"""
        conn = get_connection()
        cursor = conn.cursor()

        today = datetime.now().date()
        week_later = today + timedelta(days=7)

        # Задачи с дедлайном в ближайшую неделю
        cursor.execute(
            """
            SELECT t.*, u.telegram_id
            FROM tasks t
            JOIN users u ON t.user_id = u.telegram_id
            WHERE t.deadline BETWEEN ? AND ?
            AND t.is_completed = 0
            AND t.deadline IS NOT NULL
        """,
            (today.strftime("%Y-%m-%d"), week_later.strftime("%Y-%m-%d")),
        )

        tasks = cursor.fetchall()
        conn.close()

        for task in tasks:
            deadline_date = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
            days_left = (deadline_date - today).days

            # Отправляем напоминание если осталось меньше недели
            if days_left <= 7:
                await self.send_task_reminder(task, days_left)

    async def send_event_reminder(self, event):
        """Отправить напоминание о событии"""
        try:
            event_time = datetime.strptime(event["event_datetime"], "%Y-%m-%d %H:%M")
            formatted_time = event_time.strftime("%d.%m.%Y %H:%M")

            message = (
                f"🔔 <b>Напоминание о событии!</b>\n\n"
                f"📝 <b>{event['title']}</b>\n"
                f"📅 <b>Когда:</b> {formatted_time}\n"
            )

            if event.get("location"):
                message += f"📍 <b>Где:</b> {event['location']}\n"

            await self.bot.send_message(
                chat_id=event["telegram_id"], text=message, parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка при отправке напоминания: {e}")

    async def send_task_reminder(self, task, days_left):
        """Отправить напоминание о задаче"""
        try:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                task.get("priority", "medium"), "⚪"
            )

            if days_left <= 0:
                days_text = "СРОЧНО! Дедлайн сегодня!"
            elif days_left == 1:
                days_text = "Завтра дедлайн!"
            else:
                days_text = f"До дедлайна осталось {days_left} дней"

            message = (
                f"⏰ <b>Напоминание о задаче!</b>\n\n"
                f"📝 <b>{task['title']}</b>\n"
                f"📅 <b>Дедлайн:</b> {task['deadline']}\n"
                f"{priority_emoji} <b>Приоритет:</b> {task.get('priority', 'medium')}\n"
                f"⚠️ <b>{days_text}</b>"
            )

            await self.bot.send_message(
                chat_id=task["telegram_id"], text=message, parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка при отправке напоминания о задаче: {e}")


# Синглтон экземпляр
_reminder_service = None


def get_reminder_service(bot: Bot = None) -> ReminderService:
    """Получить экземпляр сервиса напоминаний"""
    global _reminder_service
    if _reminder_service is None and bot is not None:
        _reminder_service = ReminderService(bot)
    return _reminder_service
