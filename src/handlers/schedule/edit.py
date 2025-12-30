# src/handlers/schedule/edit.py - УПРОЩЕННАЯ ВЕРСИЯ
"""Обработчики для редактирования и удаления уроков"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from src.handlers.schedule.base import (
    delete_lesson,
    format_lesson_details,
    get_lesson,
    update_lesson,
    validate_build,
    validate_room,
    validate_subject,
    validate_teacher,
    validate_time,
)
from src.keyboards import (
    get_day_selection_keyboard,
    get_delete_confirmation_keyboard,
    get_edit_lesson_keyboard,
    get_lesson_detail_keyboard,
)
from src.states import EditLessonStates

router = Router()
logger = logging.getLogger(__name__)

# ==================== РЕДАКТИРОВАНИЕ ====================

@router.callback_query(F.data.startswith("lesson_edit_"))
async def handle_edit_lesson(callback: CallbackQuery):
    """Показать меню редактирования урока"""
    try:
        lesson_id = int(callback.data.split("_")[2])
        logger.info(f"Запрос на редактирование урока ID: {lesson_id}")

        await callback.answer()

        lesson = get_lesson(lesson_id)
        if not lesson:
            await callback.message.answer("❌ Урок не найден!")
            return

        response = format_lesson_details(lesson)
        response += "\n<b>Выберите что изменить:</b>"

        await callback.message.answer(
            response,
            reply_markup=get_edit_lesson_keyboard(lesson_id),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка в handle_edit_lesson: {e}")
        await callback.answer("❌ Ошибка при редактировании")

# ==================== УДАЛЕНИЕ ====================

@router.callback_query(F.data.startswith("lesson_delete_"))
async def handle_delete_lesson(callback: CallbackQuery):
    """Показать подтверждение удаления урока"""
    try:
        lesson_id = int(callback.data.split("_")[2])
        logger.info(f"Запрос на удаление урока ID: {lesson_id}")

        await callback.answer()

        lesson = get_lesson(lesson_id)
        if not lesson:
            await callback.message.answer("❌ Урок не найден!")
            return

        response = f"🗑️ <b>Удаление урока:</b>\n\n"
        response += f"📚 <b>Предмет:</b> {lesson['subject']}\n"
        response += f"📅 <b>День:</b> {lesson['day_of_week']}\n"
        response += f"🕒 <b>Время:</b> {lesson['start_time']}-{lesson['end_time']}\n\n"
        response += "<b>Вы действительно хотите удалить этот урок?</b>"

        await callback.message.answer(
            response,
            reply_markup=get_delete_confirmation_keyboard(lesson_id),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Ошибка в handle_delete_lesson: {e}")
        await callback.answer("❌ Ошибка при удалении")

@router.callback_query(F.data.startswith("lesson_confirm_delete_"))
async def handle_confirm_delete_lesson(callback: CallbackQuery):
    """Подтверждение и выполнение удаления урока"""
    try:
        lesson_id = int(callback.data.split("_")[3])
        logger.info(f"Подтверждение удаления урока ID: {lesson_id}")

        await callback.answer()

        success = delete_lesson(lesson_id)
        if success:
            await callback.message.answer("✅ Урок удалён!")
            # Вернуться к списку расписания
            from .view import show_schedule_list
            user_id = callback.from_user.id
            await show_schedule_list(callback.message, user_id)
        else:
            await callback.message.answer("❌ Не удалось удалить урок")
    except Exception as e:
        logger.error(f"Ошибка в handle_confirm_delete_lesson: {e}")
        await callback.answer("❌ Ошибка при удалении")

# ==================== РЕДАКТИРОВАНИЕ ПОЛЕЙ ====================

@router.callback_query(F.data.startswith("edit_field_"))
async def handle_edit_field(callback: CallbackQuery, state: FSMContext):
    """Выбрано поле урока для редактирования"""
    try:
        data_parts = callback.data.split("_")
        field_name = data_parts[2]
        lesson_id = int(data_parts[3])

        logger.info(f"Редактирование поля {field_name} урока ID: {lesson_id}")

        await callback.answer()
        await state.update_data(lesson_id=lesson_id, field_name=field_name)

        lesson = get_lesson(lesson_id)
        if not lesson:
            await callback.message.answer("❌ Урок не найден!")
            return

        if field_name == "day":
            await callback.message.answer(
                "📅 <b>Выберите новый день недели:</b>",
                reply_markup=get_day_selection_keyboard(for_edit=True, lesson_id=lesson_id),
                parse_mode="HTML",
            )
        else:
            field_names = {
                "subject": "название предмета",
                "time": "время занятия (формат: начало-конец)",
                "build": "номер корпуса (только цифры, или 'нет')",
                "room": "номер аудитории (только цифры, или 'нет')",
                "teacher": "ФИО преподавателя (или 'нет')",
            }

            current_value = lesson.get(field_name, "")

            if field_name == "time":
                current_value = f"{lesson['start_time']}-{lesson['end_time']}"

            await callback.message.answer(
                f"✏️ <b>Редактирование {field_names[field_name]}</b>\n\n"
                f"Текущее значение: <code>{current_value if current_value else 'не указано'}</code>\n\n"
                f"<b>Введите новое значение:</b>",
                parse_mode="HTML",
            )
            await state.set_state(EditLessonStates.waiting_for_field_value)
    except Exception as e:
        logger.error(f"Ошибка в handle_edit_field: {e}")
        await callback.answer("❌ Ошибка при редактировании поля")

@router.callback_query(F.data.startswith("select_day_"))
async def handle_select_day(callback: CallbackQuery):
    """Выбран новый день недели"""
    try:
        data_parts = callback.data.split("_")
        new_day = data_parts[2]
        lesson_id = int(data_parts[3])

        logger.info(f"Выбор дня {new_day} для урока ID: {lesson_id}")

        await callback.answer(f"Выбран день: {new_day}")

        success, msg = update_lesson(lesson_id, "day", new_day)
        if success:
            await callback.message.answer(
                f"✅ <b>День недели изменён на {new_day}!</b>",
                parse_mode="HTML",
            )

            # Показываем обновленный урок
            lesson = get_lesson(lesson_id)
            if lesson:
                response = format_lesson_details(lesson)
                await callback.message.answer(
                    response,
                    reply_markup=get_lesson_detail_keyboard(lesson_id),
                    parse_mode="HTML",
                )
        else:
            await callback.message.answer(f"❌ <b>{msg}</b>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка в handle_select_day: {e}")
        await callback.answer("❌ Ошибка при изменении дня")

@router.message(EditLessonStates.waiting_for_field_value)
async def handle_field_value_input(message: Message, state: FSMContext):
    """Обработка нового значения поля урока"""
    try:
        data = await state.get_data()
        lesson_id = data["lesson_id"]
        field_name = data["field_name"]
        new_value = message.text.strip()

        logger.info(f"Ввод нового значения для поля {field_name} урока ID: {lesson_id}")

        # Валидация в зависимости от поля
        is_valid = True
        error_msg = ""
        value_to_save = new_value

        if field_name == "subject":
            is_valid, error_msg = validate_subject(new_value)
        elif field_name == "time":
            is_valid, error_msg, times = validate_time(new_value)
            if is_valid:
                value_to_save = times  # (start_time, end_time)
        elif field_name == "build":
            is_valid, error_msg = validate_build(new_value)
            if is_valid and (not new_value or new_value.lower() == "нет"):
                value_to_save = None
        elif field_name == "room":
            is_valid, error_msg = validate_room(new_value)
            if is_valid and (not new_value or new_value.lower() == "нет"):
                value_to_save = None
        elif field_name == "teacher":
            is_valid, error_msg = validate_teacher(new_value)
            if is_valid and (not new_value or new_value.lower() == "нет"):
                value_to_save = None
        else:
            is_valid, error_msg = False, "Неизвестное поле"

        if not is_valid:
            await message.answer(f"❌ <b>{error_msg}</b>", parse_mode="HTML")
            return

        # Обновляем урок
        success, msg = update_lesson(lesson_id, field_name, value_to_save)

        if success:
            field_display_names = {
                "subject": "Название предмета",
                "time": "Время занятия",
                "build": "Номер корпуса",
                "room": "Номер аудитории",
                "teacher": "ФИО преподавателя",
            }

            await message.answer(
                f"✅ <b>{field_display_names[field_name]} успешно обновлено!</b>",
                parse_mode="HTML",
            )

            # Показываем обновленный урок
            lesson = get_lesson(lesson_id)
            if lesson:
                response = format_lesson_details(lesson)
                await message.answer(
                    response,
                    reply_markup=get_lesson_detail_keyboard(lesson_id),
                    parse_mode="HTML",
                )
        else:
            await message.answer(f"❌ <b>{msg}</b>", parse_mode="HTML")

        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка в handle_field_value_input: {e}")
        await message.answer("❌ Произошла ошибка при обновлении")
        await state.clear()
