# src/handlers/events/common.py
"""Общие обработчики для событий"""

from aiogram import F, Router
from aiogram.types import CallbackQuery

from src.keyboards import get_event_detail_keyboard

from .base import format_event_details, get_event

router = Router()


@router.callback_query(F.data.startswith("back_to_event_"))
async def back_to_event_handler(callback: CallbackQuery):
    """Вернуться к деталям события"""
    try:
        event_id = int(callback.data.split("_")[3])
        await callback.answer()

        event = get_event(event_id)
        if not event:
            await callback.message.answer("❌ Событие не найдено!")
            return

        response = format_event_details(event)
        await callback.message.answer(
            response,
            reply_markup=get_event_detail_keyboard(event_id),
            parse_mode="HTML",
        )
    except Exception as e:
        await callback.answer("❌ Ошибка при возврате к событию")


@router.callback_query(F.data == "events_help_btn")
async def events_help_handler(callback: CallbackQuery):
    """Помощь по событиям через inline-кнопку"""
    from src.handlers.main import show_events_help

    await callback.answer()
    await show_events_help(callback.message)


@router.callback_query(F.data == "weekday_selection_done")
async def weekday_selection_done_handler(callback: CallbackQuery):
    """Завершение выбора дней недели"""
    await callback.answer("✅ Дни недели выбраны")
    await callback.message.answer(
        "✅ Дни недели сохранены!\n\n"
        "Теперь вы можете продолжить настройку события или вернуться к нему позже."
    )
