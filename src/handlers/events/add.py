# src/handlers/events/add.py
"""Обработчики для добавления событий"""

from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from src.handlers.events.base import (
    save_event,
    validate_datetime,
    validate_description,
    validate_location,
    validate_title,
)
from src.keyboards import get_recurrence_keyboard
from src.states import EventStates

router = Router()


@router.callback_query(F.data == "add_event_btn")
async def add_event_handler(callback: CallbackQuery, state: FSMContext):
    """Начать добавление события через кнопку"""
    await callback.answer()
    await callback.message.answer(
        "🎯 <b>Добавление нового события</b>\n\nВведите название события:",
        parse_mode="HTML",
    )
    await state.set_state(EventStates.waiting_for_title)


@router.message(EventStates.waiting_for_title)
async def process_event_title(message: Message, state: FSMContext):
    """Обработка названия события"""
    title = message.text.strip()

    is_valid, error_msg = validate_title(title)
    if not is_valid:
        await message.answer(f"❌ <b>{error_msg}</b>", parse_mode="HTML")
        return

    await state.update_data(title=title)
    await message.answer(
        "📄 <b>Введите описание события (или напишите 'нет' если не нужно):</b>",
        parse_mode="HTML",
    )
    await state.set_state(EventStates.waiting_for_description)


@router.message(EventStates.waiting_for_description)
async def process_event_description(message: Message, state: FSMContext):
    """Обработка описания события"""
    description = message.text.strip()

    is_valid, error_msg = validate_description(description)
    if not is_valid:
        await message.answer(f"❌ <b>{error_msg}</b>", parse_mode="HTML")
        return

    if description.lower() == "нет" or not description:
        description = None

    await state.update_data(description=description)
    await message.answer(
        "📅 <b>Введите дату и время события (формат: ГГГГ-ММ-ДД ЧЧ:ММ):</b>\n"
        "<i>Пример: 2024-12-31 18:30</i>",
        parse_mode="HTML",
    )
    await state.set_state(EventStates.waiting_for_datetime)


@router.message(EventStates.waiting_for_datetime)
async def process_event_datetime(message: Message, state: FSMContext):
    """Обработка даты и времени события"""
    datetime_str = message.text.strip()

    is_valid, error_msg = validate_datetime(datetime_str)
    if not is_valid:
        await message.answer(f"❌ <b>{error_msg}</b>", parse_mode="HTML")
        return

    await state.update_data(event_datetime=datetime_str)
    await message.answer(
        "📍 <b>Введите место события (или напишите 'нет' если не нужно):</b>",
        parse_mode="HTML",
    )
    await state.set_state(EventStates.waiting_for_location)


@router.message(EventStates.waiting_for_location)
async def process_event_location(message: Message, state: FSMContext):
    """Обработка места события"""
    location = message.text.strip()

    is_valid, error_msg = validate_location(location)
    if not is_valid:
        await message.answer(f"❌ <b>{error_msg}</b>", parse_mode="HTML")
        return

    if location.lower() == "нет" or not location:
        location = None

    await state.update_data(location=location)
    await message.answer(
        "🔄 <b>Выберите повторяемость события:</b>",
        reply_markup=get_recurrence_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(EventStates.waiting_for_recurrence)


@router.callback_query(F.data.startswith("select_recurrence_"))
async def process_event_recurrence(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора повторяемости события"""
    recurrence = callback.data.split("_")[2]
    await callback.answer(f"Выбрана повторяемость: {recurrence}")

    # Получаем все данные из состояния
    data = await state.get_data()
    user_id = callback.from_user.id

    # Преобразуем повторяемость в формат для базы данных
    is_recurring = recurrence != "none"
    recurrence_rule = None if recurrence == "none" else recurrence

    # Сохраняем событие
    success, event_id, msg = save_event(
        user_id,
        {**data, "is_recurring": is_recurring, "recurrence_rule": recurrence_rule},
    )

    if success:
        response = "✅ <b>Событие успешно добавлено!</b>\n\n"
        response += f"<b>Название:</b> {data['title']}\n"

        if data.get("description"):
            response += f"<b>Описание:</b> {data['description']}\n"

        event_time = datetime.strptime(data["event_datetime"], "%Y-%m-%d %H:%M")
        formatted_time = event_time.strftime("%d.%m.%Y %H:%M")
        response += f"<b>Дата и время:</b> {formatted_time}\n"

        if data.get("location"):
            response += f"<b>Место:</b> {data['location']}\n"

        recurrence_names = {
            "none": "Не повторяется",
            "daily": "Ежедневно",
            "weekly": "Еженедельно",
            "monthly": "Ежемесячно",
            "yearly": "Ежегодно",
        }
        response += (
            f"<b>Повторяемость:</b> {recurrence_names.get(recurrence, recurrence)}\n"
        )

        # Кнопка для возврата к событиям
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎯 Вернуться к событиям", callback_data="back_to_events"
                    )
                ]
            ]
        )

        await callback.message.answer(
            response, reply_markup=keyboard, parse_mode="HTML"
        )
    else:
        await callback.message.answer(f"❌ <b>{msg}</b>", parse_mode="HTML")

    await state.clear()
