# src/handlers/schedule/main.py
"""Главный файл расписания"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

# Импортируем все под-роутеры
from .add import router as add_router
from .common import router as common_router
from .edit import router as edit_router

# Импортируем функцию для показа расписания
from .view import router as view_router
from .view import show_schedule_list

router = Router()

# Включаем все под-роутеры
router.include_router(add_router)
router.include_router(view_router)
router.include_router(edit_router)
router.include_router(common_router)


@router.message(Command("add_lesson"))
async def cmd_add_lesson(message: Message):
    """Добавление урока через команду"""
    await message.answer(
        "📝 <b>Добавление нового урока</b>\n\n"
        "Используйте кнопку '📅 Расписание' в главном меню, "
        "затем нажмите '➕ Добавить урок'",
        parse_mode="HTML",
    )


@router.message(F.text == "📅 Расписание")
async def button_schedule_menu(message: Message):
    """Переход в раздел Расписание"""
    user_id = message.from_user.id
    await show_schedule_list(message, user_id)


# Экспортируем функцию для показа расписания
async def show_schedule(message: Message, user_id: int):
    """Показать расписание - экспортированная функция"""
    await show_schedule_list(message, user_id)
