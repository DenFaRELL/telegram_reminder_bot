# src/handlers/schedule/view.py
"""Обработчики для просмотра и навигации по урокам"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from src.handlers.schedule.base import (
    format_lesson_details,
    get_lesson,
    get_user_lessons,
)
from src.keyboards import (
    get_lesson_detail_keyboard,
    get_lessons_selection_keyboard,
    get_schedule_list_keyboard,
)

router = Router()


# Словарь для кэширования уроков
user_lessons_cache = {}


async def show_schedule_list(message: Message, user_id: int):
    """Показать список уроков"""
    lessons = get_user_lessons(user_id)
    user_lessons_cache[user_id] = lessons

    if not lessons:
        response = "📅 <b>Ваше расписание пусто!</b>\n\n"
        response += "Добавьте первый урок с помощью кнопки ниже:"

        await message.answer(
            response,
            reply_markup=get_schedule_list_keyboard(),
            parse_mode="HTML",
        )
        return

    response = "📅 <b>Ваше расписание:</b>\n\n"
    response += "<i>Выберите урок для просмотра деталей:</i>\n\n"

    current_day = None
    for i, lesson in enumerate(lessons[:5], 1):
        day = lesson["day_of_week"]
        if day != current_day:
            if current_day is not None:
                response += "\n"
            response += f"<b>───────── {day} ─────────</b>\n\n"
            current_day = day

        subject = lesson["subject"]
        start_time = lesson["start_time"]
        end_time = lesson["end_time"]

        response += f"<b>{i}.</b> {start_time}-{end_time} - {subject}\n"

    await message.answer(
        response,
        reply_markup=get_lessons_selection_keyboard(lessons),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("view_lesson_"))
async def view_lesson_handler(callback: CallbackQuery):
    """Показать детали урока"""
    lesson_id = int(callback.data.split("_")[2])
    await callback.answer()

    lesson = get_lesson(lesson_id)
    if not lesson:
        await callback.message.answer("❌ Урок не найден!")
        return

    response = format_lesson_details(lesson)
    await callback.message.answer(
        response, reply_markup=get_lesson_detail_keyboard(lesson_id), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("lessons_page_"))
async def lessons_page_handler(callback: CallbackQuery):
    """Обработка переключения страниц уроков"""
    start_index = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    await callback.answer()

    lessons = user_lessons_cache.get(user_id, [])
    if not lessons:
        await callback.message.answer("❌ Список уроков пуст!")
        return

    response = "📅 <b>Ваше расписание:</b>\n\n"
    response += "<i>Выберите урок для просмотра деталей:</i>\n\n"

    current_day = None
    displayed_count = 0

    for i in range(start_index, len(lessons)):
        if displayed_count >= 5:
            break

        lesson = lessons[i]
        day = lesson["day_of_week"]
        if day != current_day:
            if current_day is not None and displayed_count > 0:
                response += "\n"
            response += f"<b>───────── {day} ─────────</b>\n\n"
            current_day = day

        subject = lesson["subject"]
        start_time = lesson["start_time"]
        end_time = lesson["end_time"]

        response += f"<b>{i + 1}.</b> {start_time}-{end_time} - {subject}\n"
        displayed_count += 1

    await callback.message.answer(
        response,
        reply_markup=get_lessons_selection_keyboard(lessons, start_index),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "back_to_schedule")
async def back_to_schedule_handler(callback: CallbackQuery):
    """Вернуться к списку расписания"""
    await callback.answer()
    user_id = callback.from_user.id
    await show_schedule_list(callback.message, user_id)
