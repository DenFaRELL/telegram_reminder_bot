# src/handlers/events/main.py
"""Главный файл событий"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

# Импортируем все под-роутеры
from src.handlers.events.add import router as add_router
from src.handlers.events.common import (
    router as common_router,  # Добавляем общие обработчики
)
from src.handlers.events.edit import router as edit_router

# Импортируем функцию для показа событий
from src.handlers.events.view import router as view_router
from src.handlers.events.view import show_events_list

router = Router()

# Включаем все под-роутеры
router.include_router(add_router)
router.include_router(view_router)
router.include_router(edit_router)
router.include_router(common_router)  # Добавляем общие обработчики


@router.message(F.text == "🎯 События")
async def button_events_menu(message: Message):
    """Переход в раздел Событий"""
    user_id = message.from_user.id
    await show_events_list(message, user_id)


@router.message(Command("events"))
async def cmd_events(message: Message):
    """Команда для событий"""
    user_id = message.from_user.id
    await show_events_list(message, user_id)


# Экспортируем функцию для показа событий
async def show_events(message: Message, user_id: int):
    """Показать события - экспортированная функция"""
    await show_events_list(message, user_id)
