# src/handlers/tasks/common.py
"""Общие обработчики для задач"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from src.handlers.tasks.base import format_task_details, get_task
from src.keyboards import get_task_detail_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("back_to_task_"))
async def handle_back_to_task(callback: CallbackQuery):
    """Вернуться к деталям задачи"""
    try:
        task_id = int(callback.data.split("_")[3])
        logger.info(f"Возврат к задаче ID: {task_id}")

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
        logger.error(f"Ошибка в handle_back_to_task: {e}")
        await callback.answer("❌ Ошибка при возврате к задаче")


@router.callback_query(F.data == "tasks_help_btn")
async def handle_tasks_help(callback: CallbackQuery):
    """Помощь по задачам через inline-кнопку"""
    try:
        logger.info(f"Запрос помощи по задачам. Пользователь: {callback.from_user.id}")

        await callback.answer()
        from src.handlers.main import show_tasks_help
        await show_tasks_help(callback.message)
    except Exception as e:
        logger.error(f"Ошибка в handle_tasks_help: {e}")
        await callback.answer("❌ Ошибка при показе помощи")
