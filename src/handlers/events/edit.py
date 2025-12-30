# src/handlers/events/edit.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from src.keyboards import (
    get_delete_event_confirmation_keyboard,
    get_edit_event_keyboard,
    get_event_detail_keyboard,
    get_recurrence_keyboard,
)
from src.states import EditEventStates

from .base import (
    delete_event,
    format_event_details,
    get_event,
    update_event,
    validate_datetime,
    validate_description,
    validate_event_title,
    validate_location,
    validate_recurrence,
)

router = Router()
logger = logging.getLogger(__name__)


# ==================== РЕДАКТИРОВАНИЕ ====================


@router.callback_query(F.data.regexp(r"^edit_event_[0-9]+$"))
async def handle_edit_event(callback: CallbackQuery):
    """Показать меню редактирования события (формат: edit_event_123)"""
    try:
        # Получаем event_id - формат: "edit_event_{event_id}"
        event_id = int(callback.data.split("_")[2])
        logger.info(f"Запрос на редактирование события ID: {event_id}")

        await callback.answer()

        event = get_event(event_id)
        if not event:
            await callback.message.answer("❌ Событие не найдено!")
            return

        response = format_event_details(event)
        response += "\n<b>Выберите что изменить:</b>"

        await callback.message.answer(
            response,
            reply_markup=get_edit_event_keyboard(event_id),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка в handle_edit_event: {e}")
        await callback.answer("❌ Ошибка при редактировании")


# ==================== УДАЛЕНИЕ ====================


@router.callback_query(F.data.regexp(r"^delete_event_[0-9]+$"))
async def handle_delete_event(callback: CallbackQuery):
    """Показать подтверждение удаления события (формат: delete_event_123)"""
    try:
        # Получаем event_id - формат: "delete_event_{event_id}"
        event_id = int(callback.data.split("_")[2])
        logger.info(f"Запрос на удаление события ID: {event_id}")

        await callback.answer()

        event = get_event(event_id)
        if not event:
            await callback.message.answer("❌ Событие не найдено!")
            return

        # Форматируем дату для отображения
        event_datetime = event["event_datetime"]
        try:
            from datetime import datetime
            dt = datetime.strptime(event_datetime, "%Y-%m-%d %H:%M")
            formatted_date = dt.strftime("%d.%m.%Y %H:%M")
        except:
            formatted_date = event_datetime

        response = f"🗑️ <b>Удаление события:</b>\n\n"
        response += f"📝 <b>Название:</b> {event['title']}\n"
        response += f"📅 <b>Дата и время:</b> {formatted_date}\n\n"
        response += "<b>Вы действительно хотите удалить это событие?</b>"

        await callback.message.answer(
            response,
            reply_markup=get_delete_event_confirmation_keyboard(event_id),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Ошибка в handle_delete_event: {e}")
        await callback.answer("❌ Ошибка при удалении")


@router.callback_query(F.data.regexp(r"^confirm_delete_event_[0-9]+$"))
async def handle_confirm_delete_event(callback: CallbackQuery):
    """Подтверждение и выполнение удаления события (формат: confirm_delete_event_123)"""
    try:
        # Получаем event_id - формат: "confirm_delete_event_{event_id}"
        event_id = int(callback.data.split("_")[3])
        logger.info(f"Подтверждение удаления события ID: {event_id}")

        await callback.answer()

        success = delete_event(event_id)
        if success:
            await callback.message.answer("✅ Событие удалено!")
            # Вернуться к списку событий
            from .view import show_events_list
            user_id = callback.from_user.id
            await show_events_list(callback.message, user_id)
        else:
            await callback.message.answer("❌ Не удалось удалить событие")
    except Exception as e:
        logger.error(f"Ошибка в handle_confirm_delete_event: {e}")
        await callback.answer("❌ Ошибка при удалении")


# ==================== РЕДАКТИРОВАНИЕ ПОЛЕЙ ====================


@router.callback_query(F.data.regexp(r"^edit_event_field_(title|description|datetime|location|recurrence)_[0-9]+$"))
async def handle_edit_event_field(callback: CallbackQuery, state: FSMContext):
    """Выбрано поле события для редактирования"""
    try:
        # Получаем данные - формат: "edit_event_field_{field_name}_{event_id}"
        data_parts = callback.data.split("_")

        if len(data_parts) != 5:
            logger.error(f"Неверный формат callback_data: {callback.data}")
            await callback.answer("❌ Ошибка формата")
            return

        field_name = data_parts[3]
        event_id = int(data_parts[4])

        logger.info(f"Редактирование поля {field_name} события ID: {event_id}")

        await callback.answer()
        await state.update_data(event_id=event_id, field_name=field_name)

        event = get_event(event_id)
        if not event:
            await callback.message.answer("❌ Событие не найдено!")
            return

        if field_name == "recurrence":
            await callback.message.answer(
                "🔄 <b>Выберите новое правило повторяемости:</b>",
                reply_markup=get_recurrence_keyboard(for_edit=True, event_id=event_id),
                parse_mode="HTML",
            )
        else:
            field_names = {
                "title": "название события",
                "description": "описание (или 'нет')",
                "datetime": "дату и время (формат: ГГГГ-ММ-ДД ЧЧ:ММ)",
                "location": "место проведения (или 'нет')",
            }

            current_value = event.get(field_name, "")

            # Для даты получаем из event_datetime
            if field_name == "datetime":
                current_value = event.get("event_datetime", "")

            # Форматируем для отображения
            if field_name == "datetime" and current_value:
                try:
                    from datetime import datetime
                    dt = datetime.strptime(current_value, "%Y-%m-%d %H:%M")
                    current_value = dt.strftime("%d.%m.%Y %H:%M")
                except:
                    pass

            await callback.message.answer(
                f"✏️ <b>Редактирование {field_names[field_name]}</b>\n\n"
                f"Текущее значение: <code>{current_value if current_value else 'не указано'}</code>\n\n"
                f"<b>Введите новое значение:</b>",
                parse_mode="HTML",
            )
            await state.set_state(EditEventStates.waiting_for_field_value)
    except Exception as e:
        logger.error(f"Ошибка в handle_edit_event_field: {e}")
        await callback.answer("❌ Ошибка при редактировании поля")


@router.callback_query(F.data.regexp(r"^select_recurrence_(none|daily|weekly|monthly|yearly)(_[0-9]+)?$"))
async def handle_select_recurrence(callback: CallbackQuery):
    """Выбрано новое правило повторяемости"""
    try:
        # Получаем данные - возможные форматы:
        # 1. Для нового события: "select_recurrence_{type}"
        # 2. Для редактирования: "select_recurrence_{type}_{event_id}"
        parts = callback.data.split("_")

        if len(parts) == 3:
            # Для нового события
            recurrence_type = parts[2]
            event_id = None
        elif len(parts) == 4:
            # Для редактирования (формат: select_recurrence_TYPE_EVENTID)
            recurrence_type = parts[2]
            event_id = int(parts[3])
        else:
            logger.error(f"Неверный формат callback_data: {callback.data}")
            await callback.answer("❌ Ошибка формата")
            return

        logger.info(f"Выбор повторяемости {recurrence_type} для события ID: {event_id}")

        # Преобразуем в удобочитаемый текст
        recurrence_text = {
            "none": "❌ Не повторяется",
            "daily": "📅 Ежедневно",
            "weekly": "📅 Еженедельно",
            "monthly": "📅 Ежемесячно",
            "yearly": "📅 Ежегодно"
        }.get(recurrence_type, recurrence_type)

        await callback.answer(f"Выбрано: {recurrence_text}")

        if event_id:
            # Для редактирования существующего события
            success, msg = update_event(event_id, "recurrence_rule", recurrence_type)
            if success:
                await callback.message.answer(
                    f"✅ <b>Повторяемость изменена на {recurrence_text}!</b>",
                    parse_mode="HTML",
                )

                # Показываем обновленное событие
                event = get_event(event_id)
                if event:
                    response = format_event_details(event)
                    await callback.message.answer(
                        response,
                        reply_markup=get_event_detail_keyboard(event_id),
                        parse_mode="HTML",
                    )
            else:
                await callback.message.answer(f"❌ <b>{msg}</b>", parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка в handle_select_recurrence: {e}")
        await callback.answer("❌ Ошибка при изменении повторяемости")


@router.message(EditEventStates.waiting_for_field_value)
async def handle_event_field_value_input(message: Message, state: FSMContext):
    """Обработка нового значения поля события"""
    try:
        data = await state.get_data()
        event_id = data["event_id"]
        field_name = data["field_name"]
        new_value = message.text.strip()

        logger.info(f"Ввод нового значения для поля {field_name} события ID: {event_id}")

        # Валидация в зависимости от поля
        is_valid = True
        error_msg = ""
        value_to_save = new_value

        if field_name == "title":
            is_valid, error_msg = validate_event_title(new_value)
        elif field_name == "description":
            is_valid, error_msg = validate_description(new_value)
            if is_valid and (not new_value or new_value.lower() == "нет"):
                value_to_save = None
        elif field_name == "datetime":
            is_valid, error_msg, event_datetime = validate_datetime(new_value)
            if is_valid:
                value_to_save = event_datetime
        elif field_name == "location":
            is_valid, error_msg = validate_location(new_value)
            if is_valid and (not new_value or new_value.lower() == "нет"):
                value_to_save = None
        else:
            is_valid, error_msg = False, "Неизвестное поле"

        if not is_valid:
            await message.answer(f"❌ <b>{error_msg}</b>", parse_mode="HTML")
            return

        # Обновляем событие
        # Преобразуем имя поля для базы данных
        db_field_name = field_name
        if field_name == "datetime":
            db_field_name = "event_datetime"

        success, msg = update_event(event_id, db_field_name, value_to_save)

        if success:
            field_display_names = {
                "title": "Название события",
                "description": "Описание",
                "datetime": "Дата и время",
                "location": "Место проведения",
            }

            await message.answer(
                f"✅ <b>{field_display_names[field_name]} успешно обновлено!</b>",
                parse_mode="HTML",
            )

            # Показываем обновленное событие
            event = get_event(event_id)
            if event:
                response = format_event_details(event)
                await message.answer(
                    response,
                    reply_markup=get_event_detail_keyboard(event_id),
                    parse_mode="HTML",
                )
        else:
            await message.answer(f"❌ <b>{msg}</b>", parse_mode="HTML")

        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка в handle_event_field_value_input: {e}")
        await message.answer("❌ Произошла ошибка при обновлении")
        await state.clear()
