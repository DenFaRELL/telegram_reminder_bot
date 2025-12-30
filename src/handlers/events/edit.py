# src/handlers/events/edit.py
"""Обработчики для редактирования и удаления событий"""

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
    delete_event,
    format_event_details,
    get_event,
    update_event,
    validate_datetime,
    validate_description,
    validate_location,
    validate_title,
)
from src.keyboards import (
    get_delete_event_confirmation_keyboard,
    get_edit_event_keyboard,
    get_event_detail_keyboard,
    get_recurrence_keyboard,
)
from src.states import EditEventStates

router = Router()


@router.callback_query(F.data.startswith("edit_event_"))
async def edit_event_selected(callback: CallbackQuery):
    """Выбрано событие для редактирования"""
    event_id = int(callback.data.split("_")[2])
    await callback.answer()

    event = get_event(event_id)
    if not event:
        await callback.message.answer("❌ Событие не найдено!")
        return

    response = format_event_details(event)
    response += "\n<b>Выберите что изменить:</b>"

    await callback.message.answer(
        response, reply_markup=get_edit_event_keyboard(event_id), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("delete_event_"))
async def delete_event_selected(callback: CallbackQuery):
    """Выбрано событие для удаления"""
    event_id = int(callback.data.split("_")[2])
    await callback.answer()

    event = get_event(event_id)
    if not event:
        await callback.message.answer("❌ Событие не найдено!")
        return

    response = f"🗑️ <b>Удаление события:</b>\n\n"
    response += f"📝 <b>Название:</b> {event['title']}\n"

    event_time = datetime.strptime(event["event_datetime"], "%Y-%m-%d %H:%M")
    formatted_time = event_time.strftime("%d.%m.%Y %H:%M")
    response += f"📅 <b>Дата и время:</b> {formatted_time}\n"

    response += "\n<b>Вы действительно хотите удалить это событие?</b>"

    await callback.message.answer(
        response,
        reply_markup=get_delete_event_confirmation_keyboard(event_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("confirm_delete_event_"))
async def confirm_delete_event(callback: CallbackQuery):
    """Подтверждение удаления события"""
    event_id = int(callback.data.split("_")[3])
    await callback.answer()

    success = delete_event(event_id)
    if success:
        await callback.message.answer("✅ Событие удалено!")

        # Показываем обновленный список событий
        user_id = callback.from_user.id
        from .view import show_events_list

        await show_events_list(callback.message, user_id)
    else:
        await callback.message.answer("❌ Не удалось удалить событие")


@router.callback_query(F.data.startswith("edit_event_field_"))
async def edit_event_field_selected(callback: CallbackQuery, state: FSMContext):
    """Выбрано поле события для редактирования"""
    data_parts = callback.data.split("_")
    field_name = data_parts[3]
    event_id = int(data_parts[4])

    await callback.answer()
    await state.update_data(event_id=event_id, field_name=field_name)

    event = get_event(event_id)
    if not event:
        await callback.message.answer("❌ Событие не найдено!")
        return

    if field_name == "recurrence":
        current_recurrence = (
            event.get("recurrence_rule", "none")
            if event.get("is_recurring")
            else "none"
        )
        await callback.message.answer(
            "🔄 <b>Выберите новую повторяемость события:</b>",
            reply_markup=get_recurrence_keyboard(for_edit=True, event_id=event_id),
            parse_mode="HTML",
        )
    else:
        field_names = {
            "title": "название события",
            "description": "описание события (или 'нет' если не нужно)",
            "datetime": "дата и время события (формат: ГГГГ-ММ-ДД ЧЧ:ММ)",
            "location": "место события (или 'нет' если не нужно)",
        }

        current_value = event.get(field_name, "")
        if field_name == "datetime" and current_value:
            event_time = datetime.strptime(current_value, "%Y-%m-%d %H:%M")
            current_value = event_time.strftime("%Y-%m-%d %H:%M")

        await callback.message.answer(
            f"✏️ <b>Редактирование {field_names[field_name]}</b>\n\n"
            f"Текущее значение: <code>{current_value if current_value else 'не указано'}</code>\n\n"
            f"<b>Введите новое значение:</b>",
            parse_mode="HTML",
        )
        await state.set_state(EditEventStates.waiting_for_field_value)


@router.callback_query(F.data.startswith("select_recurrence_"))
async def select_new_recurrence(callback: CallbackQuery, state: FSMContext):
    """Выбрана новая повторяемость (для добавления и редактирования)"""
    data_parts = callback.data.split("_")
    new_recurrence = data_parts[2]

    await callback.answer(f"Выбрана повторяемость: {new_recurrence}")

    # Проверяем, в каком состоянии мы находимся
    current_state = await state.get_state()

    if current_state and current_state.startswith("EditEventStates"):
        # Редактирование существующего события
        data = await state.get_data()
        event_id = data.get("event_id")

        if event_id:
            success, msg = update_event(event_id, "recurrence", new_recurrence)
            if success:
                recurrence_names = {
                    "none": "Не повторяется",
                    "daily": "Ежедневно",
                    "weekly": "Еженедельно",
                    "monthly": "Ежемесячно",
                    "yearly": "Ежегодно",
                }

                await callback.message.answer(
                    f"✅ <b>Повторяемость события изменена на {recurrence_names.get(new_recurrence, new_recurrence)}!</b>",
                    parse_mode="HTML",
                )

                # Показываем обновленное событие
                event = get_event(event_id)
                if event:
                    response = format_event_details(event)
                    keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="🎯 Вернуться к событию",
                                    callback_data=f"view_event_{event_id}",
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
        else:
            # Это для добавления нового события
            # Данные уже должны быть в состоянии
            pass
    else:
        # Добавление нового события - эта часть уже должна быть в add.py
        pass


@router.message(EditEventStates.waiting_for_field_value)
async def process_event_field_value(message: Message, state: FSMContext):
    """Обработка нового значения поля события"""
    data = await state.get_data()
    event_id = data["event_id"]
    field_name = data["field_name"]
    new_value = message.text.strip()

    # Валидация в зависимости от поля
    is_valid = True
    error_msg = ""

    if field_name == "title":
        is_valid, error_msg = validate_title(new_value)
    elif field_name == "description":
        is_valid, error_msg = validate_description(new_value)
        if is_valid and (not new_value or new_value.lower() == "нет"):
            new_value = None
    elif field_name == "datetime":
        is_valid, error_msg = validate_datetime(new_value)
    elif field_name == "location":
        is_valid, error_msg = validate_location(new_value)
        if is_valid and (not new_value or new_value.lower() == "нет"):
            new_value = None
    else:
        is_valid, error_msg = False, "Неизвестное поле"

    if not is_valid:
        await message.answer(f"❌ <b>{error_msg}</b>", parse_mode="HTML")
        return

    # Обновляем событие
    success, msg = update_event(event_id, field_name, new_value)

    if success:
        field_display_names = {
            "title": "Название события",
            "description": "Описание события",
            "datetime": "Дата и время события",
            "location": "Место события",
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


# Обработчик для возврата к событию
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
