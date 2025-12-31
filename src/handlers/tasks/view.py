# src/handlers/tasks/view.py
"""Обработчики для просмотра задач"""

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from src.handlers.tasks.base import (
    format_task_details,
    format_task_preview,
    get_task,
    get_user_tasks,
)
from src.keyboards import (
    get_task_detail_keyboard,
    get_tasks_list_keyboard,
    get_tasks_selection_keyboard,
)

router = Router()
logger = logging.getLogger(__name__)

# Словарь для кэширования задач
user_tasks_cache = {}


async def show_tasks_list(message: Message, user_id: int):
    """Показать список задач"""
    try:
        logger.info(f"Показать список задач для пользователя ID: {user_id}")

        # Получаем задачи
        active_tasks = get_user_tasks(user_id, only_active=True)
        all_tasks = get_user_tasks(user_id, only_active=False)
        completed_tasks = [t for t in all_tasks if t.get("is_completed") == 1]

        # === ОТЛАДКА завершенных задач ===
        logger.info(f"Все задачи (all_tasks): {len(all_tasks)} шт")
        logger.info(f"Активные задачи: {len(active_tasks)} шт")
        logger.info(f"Завершенные задачи: {len(completed_tasks)} шт")

        # Выведите ID завершенных задач
        completed_ids = [t['id'] for t in completed_tasks]
        logger.info(f"ID завершенных задач: {completed_ids}")
        # === КОНЕЦ ОТЛАДКИ ===

        logger.info(f"Активных задач: {len(active_tasks)}, завершенных: {len(completed_tasks)}")

        # Кэшируем активные задачи для пагинации
        user_tasks_cache[user_id] = active_tasks

        # Формируем ответ
        if not active_tasks and not completed_tasks:
            response = "✅ <b>У вас пока нет задач!</b>\n\n"
            response += "Добавьте первую задачу с помощью кнопки ниже:"
            keyboard = get_tasks_list_keyboard()
        else:
            response = "✅ <b>Ваши задачи:</b>\n\n"

            if active_tasks:
                response += "<i>Выберите активную задачу для просмотра деталей:</i>\n\n"
                response += "📋 <b>Активные задачи:</b>\n\n"

                for i, task in enumerate(active_tasks[:5], 1):
                    title = task["title"]
                    response += f"<b>{i}.</b> {title}\n"

                if task.get("deadline"):
                    # Форматируем дату
                    try:
                        deadline_str = task["deadline"]
                        # Пробуем разные форматы
                        date_obj = None
                        for fmt in ["%Y-%m-%d", "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]:
                            try:
                                date_obj = datetime.strptime(deadline_str, fmt)
                                break
                            except ValueError:
                                continue

                        if date_obj:
                            formatted_deadline = date_obj.strftime("%d.%m.%Y")
                            response += f"📅 <i>До: {formatted_deadline}</i>\n"
                        else:
                            response += f"📅 <i>До: {deadline_str}</i>\n"
                    except Exception as e:
                        logger.error(f"Ошибка форматирования даты {task['deadline']}: {e}")
                        response += f"📅 <i>До: {task['deadline']}</i>\n"

                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                        task.get("priority", "medium"), "⚪"
                    )

                    response += f"{priority_emoji} <i>Приоритет: {task.get('priority', 'medium')}</i>\n\n"

            if completed_tasks:
                response += "\n🏁 <b>Завершённые задачи:</b>\n"
                response += f"<i>Всего завершено: {len(completed_tasks)}</i>\n\n"

                # Показываем последние 3 завершенные задачи (самые новые)
                recent_completed = completed_tasks[-3:]  # Берем последние 3
                recent_completed.reverse()  # Переворачиваем, чтобы самые новые были первыми

                for i, task in enumerate(recent_completed, 1):
                    title = task["title"][:25] + "..." if len(task["title"]) > 25 else task["title"]
                    response += f"✅ <b>{title}</b>\n"

                    if task.get("deadline"):
                        # Форматируем дату из ГГГГ-ММ-ДД в ДД.ММ.ГГГГ
                        try:
                            deadline_date = datetime.strptime(task["deadline"], "%Y-%m-%d")
                            formatted_deadline = deadline_date.strftime("%d.%m.%Y")
                            response += f"📅 <i>До: {formatted_deadline}</i>\n"
                        except:
                            response += f"📅 <i>До: {task['deadline']}</i>\n"

                    if i < len(recent_completed):
                        response += "\n"

            # Выбираем клавиатуру
            if active_tasks:
                keyboard = get_tasks_selection_keyboard(active_tasks)
            else:
                keyboard = get_tasks_list_keyboard()

        # Отправляем сообщение
        await message.answer(
            response,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Ошибка в show_tasks_list: {e}", exc_info=True)
        await message.answer("❌ Ошибка при загрузке списка задач")


@router.callback_query(F.data.startswith("view_task_"))
async def handle_view_task(callback: CallbackQuery):
    """Показать детали задачи"""
    try:
        task_id = int(callback.data.split("_")[2])
        logger.info(f"Просмотр деталей задачи ID: {task_id}")

        await callback.answer()

        task = get_task(task_id)
        if not task:
            await callback.message.answer("❌ Задача не найдена!")
            return

        response = format_task_details(task)
        await callback.message.answer(
            response,
            reply_markup=get_task_detail_keyboard(task_id),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка в handle_view_task: {e}")
        await callback.answer("❌ Ошибка при загрузке задачи")


@router.callback_query(F.data.startswith("tasks_page_"))
async def handle_tasks_page(callback: CallbackQuery):
    """Обработка переключения страниц задач"""
    try:
        start_index = int(callback.data.split("_")[2])
        user_id = callback.from_user.id
        logger.info(f"Переключение страницы задач. Пользователь: {user_id}, старт: {start_index}")

        await callback.answer()

        tasks = user_tasks_cache.get(user_id, [])
        if not tasks:
            await callback.message.answer("❌ Список задач пуст!")
            return

        response = "✅ <b>Активные задачи:</b>\n\n"
        response += "<i>Выберите задачу для просмотра деталей:</i>\n\n"

        for i, task in enumerate(tasks[start_index : start_index + 5], 1):
            title = task["title"]
            response += f"<b>{start_index + i}.</b> {title}\n"

        if task.get("deadline"):
            # Форматируем дату
            try:
                deadline_str = task["deadline"]
                # Пробуем разные форматы
                date_obj = None
                for fmt in ["%Y-%m-%d", "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]:
                    try:
                        date_obj = datetime.strptime(deadline_str, fmt)
                        break
                    except ValueError:
                        continue

                if date_obj:
                    formatted_deadline = date_obj.strftime("%d.%m.%Y")
                    response += f"📅 <i>До: {formatted_deadline}</i>\n"
                else:
                    response += f"📅 <i>До: {deadline_str}</i>\n"
            except Exception as e:
                logger.error(f"Ошибка форматирования даты {task['deadline']}: {e}")
                response += f"📅 <i>До: {task['deadline']}</i>\n"

            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                task.get("priority", "medium"), "⚪"
            )

            response += (
                f"{priority_emoji} <i>Приоритет: {task.get('priority', 'medium')}</i>\n\n"
            )

        await callback.message.answer(
            response,
            reply_markup=get_tasks_selection_keyboard(tasks, start_index),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Ошибка в handle_tasks_page: {e}")
        await callback.answer("❌ Ошибка при переключении страницы")


@router.callback_query(F.data == "back_to_tasks")
async def handle_back_to_tasks(callback: CallbackQuery):
    """Вернуться к списку задач"""
    try:
        user_id = callback.from_user.id
        logger.info(f"Возврат к списку задач. Пользователь: {user_id}")

        await callback.answer()
        await show_tasks_list(callback.message, user_id)
    except Exception as e:
        logger.error(f"Ошибка в handle_back_to_tasks: {e}")
        await callback.answer("❌ Ошибка при возврате к списку")
