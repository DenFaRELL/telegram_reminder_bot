# src/handlers/events/common.py
"""Общие обработчики для событий"""

from aiogram import F, Router
from aiogram.types import CallbackQuery

from src.handlers.events.base import format_event_details, get_event
from src.keyboards import get_event_detail_keyboard

router = Router()


@router.callback_query(F.data.startswith("back_to_event_"))
async def back_to_event_handler(callback: CallbackQuery):
    """Вернуться к деталям события"""
    event_id = int(callback.data.split("_")[3])
    await callback.answer()

    event = get_event(event_id)
    if not event:
        await callback.message.answer("❌ Событие не найдено!")
        return

    response = format_event_details(event)
    await callback.message.answer(
        response, reply_markup=get_event_detail_keyboard(event_id), parse_mode="HTML"
    )
