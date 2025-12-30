# src/handlers/schedule/common.py
"""Общие обработчики для расписания"""

from aiogram import F, Router
from aiogram.types import CallbackQuery

from src.handlers.schedule.base import format_lesson_details, get_lesson
from src.keyboards import get_lesson_detail_keyboard

router = Router()


@router.callback_query(F.data.startswith("back_to_lesson_"))
async def back_to_lesson_handler(callback: CallbackQuery):
    """Вернуться к деталям урока"""
    lesson_id = int(callback.data.split("_")[3])
    await callback.answer()

    lesson = get_lesson(lesson_id)
    if not lesson:
        await callback.message.answer("❌ Урок не найден!")
        return

    response = format_lesson_details(lesson)
    await callback.message.answer(
        response, reply_markup=get_lesson_detail_keyboard(lesson_id), parse_mode="HTML"
    )


@router.callback_query(F.data == "schedule_help_btn")
async def schedule_help_handler(callback: CallbackQuery):
    """Помощь по расписанию через inline-кнопку"""
    from src.handlers.main import show_schedule_help

    await callback.answer()
    await show_schedule_help(callback.message)
