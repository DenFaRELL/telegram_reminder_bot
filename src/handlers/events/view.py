# src/handlers/events/view.py
"""Обработчики для просмотра событий"""

from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from src.handlers.events.base import format_event_details, get_event, get_user_events
from src.keyboards import (
    get_event_detail_keyboard,
    get_events_list_keyboard,
    get_events_selection_keyboard,
)

router = Router()

# Словарь для кэширования событий
user_events_cache = {}


async def show_events_list(message: Message, user_id: int):
    """Показать список событий"""
    events = get_user_events(user_id, upcoming_only=True)
    user_events_cache[user_id] = events

    if not events:
        response = "🎯 <b>У вас пока нет событий!</b>\n\n"
        response += "Добавьте первое событие с помощью кнопки ниже:"

        await message.answer(
            response,
            reply_markup=get_events_list_keyboard(),
            parse_mode="HTML",
        )
        return

    response = "🎯 <b>Ваши события:</b>\n\n"
    response += "<i>Выберите событие для просмотра деталей:</i>\n\n"

    for i, event in enumerate(events[:5], 1):
        title = event["title"]
        event_time = datetime.strptime(event["event_datetime"], "%Y-%m-%d %H:%M")
        formatted_date = event_time.strftime("%d.%m.%Y")
        formatted_time = event_time.strftime("%H:%M")

        response += f"<b>{i}.</b> {formatted_date} {formatted_time} - {title}\n\n"

    await message.answer(
        response,
        reply_markup=get_events_selection_keyboard(events),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("view_event_"))
async def view_event_handler(callback: CallbackQuery):
    """Показать детали события"""
    event_id = int(callback.data.split("_")[2])
    await callback.answer()

    event = get_event(event_id)
    if not event:
        await callback.message.answer("❌ Событие не найдено!")
        return

    response = format_event_details(event)
    await callback.message.answer(
        response, reply_markup=get_event_detail_keyboard(event_id), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("events_page_"))
async def events_page_handler(callback: CallbackQuery):
    """Обработка переключения страниц событий"""
    start_index = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    await callback.answer()

    events = user_events_cache.get(user_id, [])
    if not events:
        await callback.message.answer("❌ Список событий пуст!")
        return

    response = "🎯 <b>Ваши события:</b>\n\n"
    response += "<i>Выберите событие для просмотра деталей:</i>\n\n"

    for i, event in enumerate(events[start_index : start_index + 5], 1):
        title = event["title"]
        event_time = datetime.strptime(event["event_datetime"], "%Y-%m-%d %H:%M")
        formatted_date = event_time.strftime("%d.%m.%Y")
        formatted_time = event_time.strftime("%H:%M")

        response += (
            f"<b>{start_index + i}.</b> {formatted_date} {formatted_time} - {title}\n\n"
        )

    await callback.message.answer(
        response,
        reply_markup=get_events_selection_keyboard(events, start_index),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "back_to_events")
async def back_to_events_handler(callback: CallbackQuery):
    """Вернуться к списку событий"""
    await callback.answer()
    user_id = callback.from_user.id
    await show_events_list(callback.message, user_id)


@router.callback_query(F.data == "events_help_btn")
async def events_help_handler(callback: CallbackQuery):
    """Помощь по событиям через inline-кнопку"""
    from src.handlers.main import show_events_help

    await callback.answer()
    await show_events_help(callback.message)
