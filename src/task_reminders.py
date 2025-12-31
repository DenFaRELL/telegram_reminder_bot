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
        today = now.strftime("%Y-%m-%d")

        # Ищем задачи с дедлайнами от сегодня до 30 дней вперед
        deadline_threshold = (now + timedelta(days=30)).strftime("%Y-%m-%d")

        logger.info(f"🔍 Проверка дедлайнов с {today} до {deadline_threshold}")

        cursor.execute(
            """
            SELECT t.*, u.telegram_id, u.username
            FROM tasks t
            JOIN users u ON t.user_id = u.telegram_id
            WHERE t.deadline >= ? AND t.deadline <= ?
            AND t.is_completed = 0
            AND t.deadline IS NOT NULL
            ORDER BY t.deadline
            """,
            (today, deadline_threshold)
        )

        tasks = cursor.fetchall()
        conn.close()

        logger.info(f"📊 Найдено задач с дедлайнами: {len(tasks)}")

        if tasks:
            for task in tasks:
                logger.info(f"  - ID {task['id']}: '{task['title'][:20]}...' дедлайн {task['deadline']}")

        # Для каждой задачи проверяем нужно ли создавать напоминания
        for task in tasks:
            task_id = task["id"]

            # Проверяем когда последний раз отправляли напоминания
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_reminder_sent FROM tasks WHERE id = ?",
                (task_id,)
            )
            last_sent_result = cursor.fetchone()
            conn.close()

            last_sent = None
            if last_sent_result and last_sent_result[0]:  # Проверяем есть ли значение в первом столбце
                last_sent = last_sent_result[0]

            should_process = True

            if last_sent:
                try:
                    # Если напоминания отправлялись менее 12 часов назад - пропускаем
                    last_sent_dt = datetime.strptime(last_sent, "%Y-%m-%d %H:%M")
                    hours_since_last = (now - last_sent_dt).total_seconds() / 3600

                    if hours_since_last < 12:
                        logger.info(f"⏰ Задача {task_id} уже получала напоминания {hours_since_last:.1f} часов назад, пропускаем")
                        should_process = False
                except Exception as e:
                    logger.error(f"❌ Ошибка при разборе даты {last_sent}: {e}")

            if should_process:
                logger.info(f"📋 Обработка задачи ID {task_id}: {task['title']} (дедлайн: {task['deadline']})")
                await self.schedule_task_reminders(task)
            else:
                logger.info(f"⏰ Пропускаем задачу {task_id} - напоминания уже отправлялись недавно")

    async def schedule_task_reminders(self, task):
        """Создание напоминаний для задачи"""
        try:
            # Предполагаем, что дедлайн в 9:00 утра указанного дня
            deadline_str = task["deadline"] + " 09:00"
            deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
            now = datetime.now()
            today = now.date()

            logger.info(f"🔍 Анализ задачи {task['id']}: дедлайн {deadline_date}, сейчас {now}")

            # Пропускаем просроченные задачи
            if deadline_date < now:
                logger.info(f"⏰ Задача {task['id']} просрочена, пропускаем")
                return

            # Вычисляем сколько дней осталось до дедлайна
            # Для точного расчета используем timedelta с учетом времени
            time_until_deadline = deadline_date - now
            days_until_deadline = time_until_deadline.days
            logger.info(f"📅 До дедлайна осталось: {days_until_deadline} дней и {time_until_deadline.seconds//3600} часов")

            # Удаляем старые ненаправленные напоминания для этой задачи
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM task_reminders WHERE task_id = ? AND reminder_sent = 0",
                (task["id"],)
            )
            conn.commit()
            conn.close()
            logger.info(f"🧹 Удалены старые ненаправленные напоминания для задачи {task['id']}")

            reminder_schedule = [
                (7, 9, 0, "7d"),    # За 7 дней в 9:00
                (3, 9, 0, "3d"),    # За 3 дня в 9:00
                (1, 9, 0, "1d"),    # За 1 день в 9:00
                (1, 21, 0, "12h"),  # За 12 часов в 21:00
            ]

            created_count = 0
            for days_before, hour, minute, reminder_type in reminder_schedule:
                # Для напоминаний "за 1 день" и "за 12 часов" создаем если до дедлайна >= 12 часов
                if reminder_type in ["1d", "12h"]:
                    should_create = time_until_deadline >= timedelta(hours=12)
                else:
                    should_create = days_until_deadline >= days_before

                if should_create:
                    reminder_date = deadline_date - timedelta(days=days_before)
                    reminder_time = datetime.combine(reminder_date.date(), datetime.min.time().replace(hour=hour, minute=minute))

                    if reminder_time > now:
                        logger.info(f"⏰ Создаем напоминание типа {reminder_type} на {reminder_time}")
                        await self.create_reminder(task["id"], reminder_time, reminder_type)
                        created_count += 1

            # Обновляем время последнего напоминания
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET last_reminder_sent = ? WHERE id = ?",
                (now.strftime("%Y-%m-%d %H:%M"), task["id"])
            )
            conn.commit()
            conn.close()

            logger.info(f"✅ Создано {created_count} напоминаний для задачи {task['id']}: {task['title']}")

        except Exception as e:
            logger.error(f"❌ Ошибка при создании напоминаний для задачи {task['id']}: {e}", exc_info=True)

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
            logger.info(f"Создано напоминание для задачи {task_id}: {reminder_type} в {reminder_time}")

        conn.close()

    async def send_scheduled_reminders(self):
        """Отправка запланированных напоминаний о задачах"""
        conn = get_connection()
        cursor = conn.cursor()

        now = datetime.now()
        # Используем формат без секунд для сравнения
        now_local_str = now.strftime("%Y-%m-%d %H:%M")

        logger.info(f"🔍 Проверка напоминаний, время: {now_local_str}")

        # ИСПРАВЛЕННЫЙ ЗАПРОС: убрали strftime, сравниваем как строки
        cursor.execute("""
            SELECT r.*, t.title, t.deadline, t.description, t.priority,
                u.telegram_id, u.username
            FROM task_reminders r
            JOIN tasks t ON r.task_id = t.id
            JOIN users u ON t.user_id = u.telegram_id
            WHERE r.reminder_sent = 0
            AND r.reminder_time <= ?
            AND t.is_completed = 0
            ORDER BY r.reminder_time
        """, (now_local_str,))  # Используем формат без секунд

        reminders = cursor.fetchall()

        logger.info(f"📨 Найдено напоминаний для отправки: {len(reminders)}")

        sent_count = 0
        for reminder in reminders:
            try:
                logger.info(f"📤 Отправка напоминания {reminder['id']} для задачи {reminder['task_id']}")

                await self.send_task_reminder(reminder)
                sent_count += 1

                # Помечаем напоминание как отправленное
                cursor.execute(
                    "UPDATE task_reminders SET reminder_sent = 1 WHERE id = ?",
                    (reminder["id"],)
                )
                conn.commit()
                logger.info(f"✅ Напоминание {reminder['id']} отправлено и помечено")

            except Exception as e:
                logger.error(f"❌ Ошибка при отправке напоминания о задаче {reminder['id']}: {e}", exc_info=True)

        conn.close()

        if sent_count > 0:
            logger.info(f"🎉 Отправлено {sent_count} напоминаний о задачах")

    async def send_task_reminder(self, reminder):
        """Отправка конкретного напоминания о задаче"""
        try:
            # Преобразуем sqlite3.Row в словарь для удобства
            reminder_dict = dict(reminder)

            deadline_date = datetime.strptime(reminder_dict["deadline"], "%Y-%m-%d")
            now = datetime.now()

            # Вычисляем оставшееся время
            time_left = deadline_date.date() - now.date()
            days_left = time_left.days

            # Форматируем дату дедлайна
            formatted_date = deadline_date.strftime("%d.%m.%Y")

            # Определяем текст в зависимости от времени до дедлайна
            reminder_type = reminder_dict["reminder_type"]
            time_text = self.get_time_text(reminder_type, days_left)

            # Эмодзи приоритета
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                reminder_dict.get("priority", "medium"), "⚪"
            )

            # Создаем сообщение
            message = f"⏰ <b>Напоминание о задаче!</b>\n\n"
            message += f"📝 <b>{reminder_dict['title']}</b>\n"
            message += f"📅 <b>Дедлайн:</b> {formatted_date}\n"
            message += f"{priority_emoji} <b>Приоритет:</b> {reminder_dict.get('priority', 'medium')}\n"

            if reminder_dict.get("description"):
                desc = reminder_dict["description"]
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
                chat_id=reminder_dict["telegram_id"],
                text=message,
                parse_mode="HTML"
            )

            logger.info(f"Отправлено напоминание о задаче {reminder_dict['task_id']} пользователю {reminder_dict['telegram_id']}")

        except Exception as e:
            logger.error(f"Ошибка при формировании напоминания о задаче: {e}")
            raise

    def get_time_text(self, reminder_type: str, days_left: int) -> str:
        """Получить текстовое представление оставшегося времени"""
        if reminder_type == "12h":
            return "12 часов"  # Это будет вечером перед дедлайном
        elif reminder_type == "1d":
            if days_left == 1:
                return "1 день"
            else:
                return "менее дня"
        elif reminder_type == "3d":
            if days_left == 3:
                return "3 дня"
            else:
                return f"{days_left} дней"
        elif reminder_type == "7d":
            if days_left == 7:
                return "7 дней"
            else:
                return f"{days_left} дней"
        else:
            # Общий случай
            if days_left == 1:
                return "1 день"
            elif 2 <= days_left <= 4:
                return f"{days_left} дня"
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

# В конец файла src/task_reminders.py добавьте:
async def manual_send_reminders(bot: Bot):
    """Ручная отправка напоминаний (для отладки)"""
    service = get_task_reminder_service(bot)
    if service:
        logger.info("🔧 РУЧНОЙ ЗАПУСК отправки напоминаний")
        await service.send_scheduled_reminders()
        logger.info("✅ Ручная отправка завершена")
        return True
    return False
