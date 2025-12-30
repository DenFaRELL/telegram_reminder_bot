# src/handlers/tasks/main.py
"""Главный файл задач"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.handlers.tasks.view import show_tasks_list

# Импортируем все под-роутеры
from .add import router as add_router
from .common import router as common_router
from .edit import router as edit_router
from .view import router as view_router

router = Router()
logger = logging.getLogger(__name__)

# Включаем все под-роутеры (важен порядок!)
router.include_router(edit_router)
router.include_router(add_router)
router.include_router(view_router)
router.include_router(common_router)


# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

@router.message(F.text == "✅ Задачи")
async def handle_button_tasks_menu(message: Message):
    """Переход в раздел Задачи"""
    try:
        user_id = message.from_user.id
        logger.info(f"Переход в раздел Задачи. Пользователь: {user_id}")

        await show_tasks_list(message, user_id)
    except Exception as e:
        logger.error(f"Ошибка в handle_button_tasks_menu: {e}")
        await message.answer("❌ Ошибка при переходе в раздел задач")


@router.message(Command("tasks"))
async def handle_cmd_tasks(message: Message):
    """Команда для задач"""
    try:
        user_id = message.from_user.id
        logger.info(f"Команда /tasks. Пользователь: {user_id}")

        await show_tasks_list(message, user_id)
    except Exception as e:
        logger.error(f"Ошибка в handle_cmd_tasks: {e}")
        await message.answer("❌ Ошибка при выполнении команды")


# ==================== ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ ====================

@router.message(Command("add_task"))
async def handle_cmd_add_task(message: Message):
    """Добавление задачи через команду"""
    try:
        logger.info(f"Команда /add_task. Пользователь: {message.from_user.id}")

        await message.answer(
            "📝 <b>Добавление новой задачи</b>\n\n"
            "Используйте кнопку '✅ Задачи' в главном меню, "
            "затем нажмите '➕ Добавить задачу'",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Ошибка в handle_cmd_add_task: {e}")
        await message.answer("❌ Ошибка при выполнении команды")


@router.message(Command("my_tasks"))
async def handle_cmd_my_tasks(message: Message):
    """Показать мои задачи через команду"""
    try:
        user_id = message.from_user.id
        logger.info(f"Команда /my_tasks. Пользователь: {user_id}")

        await show_tasks_list(message, user_id)
    except Exception as e:
        logger.error(f"Ошибка в handle_cmd_my_tasks: {e}")
        await message.answer("❌ Ошибка при выполнении команды")


# ==================== ЭКСПОРТИРУЕМЫЕ ФУНКЦИИ ====================


async def show_tasks_section(message: Message, user_id: int):
    """Показать задачи - экспортированная функция для главного меню"""
    try:
        logger.info(f"Показать раздел задач. Пользователь: {user_id}")

        # Импортируем здесь, чтобы избежать циклического импорта
        from .view import show_tasks_list
        await show_tasks_list(message, user_id)

    except Exception as e:
        logger.error(f"Ошибка в show_tasks_section: {e}", exc_info=True)
        await message.answer("❌ Ошибка при загрузке раздела задач")
