# src/handlers/events.py
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.database import get_connection
from src.keyboards import (
    get_delete_event_confirmation_keyboard,
    get_edit_event_keyboard,
    get_event_detail_keyboard,
    get_events_list_keyboard,
    get_events_selection_keyboard,
    get_recurrence_keyboard,
    get_weekday_selection_keyboard,
)
from src.states import EditEventStates, EventStates

router = Router()

# Глобальная переменная для user_current_section
user_current_section = {}
# Словари для хранения временных данных
user_events_cache = {}
user_selected_weekdays = {}


async def show_events_list(message: Message, user_id):
    """Показать список событий"""
    conn = get_connection()
    cursor = conn.cursor()

    # Получаем ближайшие события (30 дней вперед)
    cursor.execute(
        """
        SELECT id, title, description, event_datetime, location, is_recurring, recurrence_rule
        FROM events
        WHERE user_id = ?
        ORDER BY event_datetime
        LIMIT 20
        """,
        (user_id,)
    )

    events = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Сохраняем события в кэш
    user_events_cache[user_id] = events

    if not events:
        response = "🎯 <b>У вас пока нет событий!</b>\n\n"
        response += "Добавьте первое событие с помощью кнопки ниже:"

        await message.answer(
            response,
            reply_markup=get_events_list_keyboard(),
            parse_mode="HTML",
        )
    else:
        response = "🎯 <b>Ваши ближайшие события:</b>\n\n"
        response += "<i>Выберите событие для просмотра деталей:</i>\n\n"

        for i, event in enumerate(events[:5], 1):
            title = event['title']
            event_datetime = event['event_datetime']

            # Форматируем дату и время
            try:
                dt = datetime.strptime(event_datetime, '%Y-%m-%d %H:%M')
                formatted_date = dt.strftime('%d.%m.%Y %H:%M')
            except:
                formatted_date = event_datetime

            response += f"<b>{i}.</b> {formatted_date} - {title}\n"

            if event['is_recurring']:
                response += "🔄 <i>Повторяющееся</i>\n"

            response += "\n"

        await message.answer(
            response,
            reply_markup=get_events_selection_keyboard(events),
            parse_mode="HTML",
        )


async def show_event_details(message_or_callback, event_id):
    """Показать детали события"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = dict(cursor.fetchone())
    conn.close()

    if not event:
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer("❌ Событие не найдено!")
        else:
            await message_or_callback.answer("❌ Событие не найдено!")
        return

    # Формируем детальное описание события
    response = "🎯 <b>Детали события:</b>\n\n"
    response += f"📝 <b>Название:</b> {event['title']}\n"

    if event['description']:
        response += f"📄 <b>Описание:</b> {event['description']}\n"

    # Форматируем дату и время
    event_datetime = event['event_datetime']
    try:
        dt = datetime.strptime(event_datetime, '%Y-%m-%d %H:%M')
        formatted_datetime = dt.strftime('%d.%m.%Y %H:%M')
        day_of_week = dt.strftime('%A')
        response += f"📅 <b>Дата и время:</b> {formatted_datetime} ({day_of_week})\n"
    except:
        response += f"📅 <b>Дата и время:</b> {event_datetime}\n"

    if event['location']:
        response += f"📍 <b>Место:</b> {event['location']}\n"

    if event['is_recurring']:
        recurrence_rules = {
            'daily': 'Ежедневно',
            'weekly': 'Еженедельно',
            'monthly': 'Ежемесячно',
            'yearly': 'Ежегодно'
        }
        recurrence = recurrence_rules.get(event['recurrence_rule'], event['recurrence_rule'])
        response += f"🔄 <b>Повторяемость:</b> {recurrence}\n"

    # Определяем куда отправлять ответ
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.answer(
            response,
            reply_markup=get_event_detail_keyboard(event_id),
            parse_mode="HTML"
        )
        await message_or_callback.answer()
    else:
        await message_or_callback.answer(
            response,
            reply_markup=get_event_detail_keyboard(event_id),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "events_help_btn")
async def events_help_handler(callback: CallbackQuery):
    """Помощь по событиям"""
    from src.handlers.main import show_events_help
    await callback.answer()
    await show_events_help(callback.message)


@router.callback_query(F.data == "add_event_btn")
async def add_event_handler(callback: CallbackQuery, state: FSMContext):
    """Начать добавление события"""
    user_id = callback.from_user.id
    user_current_section[user_id] = "events"
    await callback.answer()

    await callback.message.answer(
        "🎯 <b>Добавление нового события</b>\n\n"
        "Введите название события:",
        parse_mode="HTML"
    )

    await state.set_state(EventStates.waiting_for_title)


@router.message(EventStates.waiting_for_title)
async def process_event_title(message: Message, state: FSMContext):
    """Обработка названия события"""
    await state.update_data(title=message.text)

    await message.answer(
        "📄 <b>Введите описание события (или напишите 'нет' если не нужно):</b>",
        parse_mode="HTML"
    )

    await state.set_state(EventStates.waiting_for_description)


@router.message(EventStates.waiting_for_description)
async def process_event_description(message: Message, state: FSMContext):
    """Обработка описания события"""
    description = message.text.strip()
    if description.lower() == "нет" or not description:
        description = None

    await state.update_data(description=description)

    await message.answer(
        "📅 <b>Введите дату и время события (формат: ГГГГ-ММ-ДД ЧЧ:ММ):</b>\n"
        "<i>Пример: 2024-12-31 18:30</i>",
        parse_mode="HTML"
    )

    await state.set_state(EventStates.waiting_for_datetime)


@router.message(EventStates.waiting_for_datetime)
async def process_event_datetime(message: Message, state: FSMContext):
    """Обработка даты и времени события"""
    event_datetime = message.text.strip()

    # Проверяем формат даты и времени
    try:
        datetime.strptime(event_datetime, '%Y-%m-%d %H:%M')
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат даты и времени!</b>\n"
            "Используйте формат: ГГГГ-ММ-ДД ЧЧ:ММ\n"
            "Пример: 2024-12-31 18:30",
            parse_mode="HTML"
        )
        return

    await state.update_data(event_datetime=event_datetime)

    await message.answer(
        "📍 <b>Введите место проведения события (или напишите 'нет'):</b>",
        parse_mode="HTML"
    )

    await state.set_state(EventStates.waiting_for_location)


@router.message(EventStates.waiting_for_location)
async def process_event_location(message: Message, state: FSMContext):
    """Обработка места проведения события"""
    location = message.text.strip()
    if location.lower() == "нет" or not location:
        location = None

    await state.update_data(location=location)

    await message.answer(
        "🔄 <b>Выберите повторяемость события:</b>",
        reply_markup=get_recurrence_keyboard(),
        parse_mode="HTML"
    )

    await state.set_state(EventStates.waiting_for_recurrence)


@router.callback_query(F.data.startswith("select_weekday_"))
async def select_weekday_handler(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора дня недели для еженедельного события"""
    weekday_num = int(callback.data.split("_")[2])  # 1-7
    user_id = callback.from_user.id

    # Получаем или создаем список выбранных дней
    selected_days = user_selected_weekdays.get(user_id, [])

    # Добавляем или удаляем день
    if weekday_num in selected_days:
        selected_days.remove(weekday_num)
        await callback.answer(f"День {weekday_num} удален")
    else:
        selected_days.append(weekday_num)
        await callback.answer(f"День {weekday_num} добавлен")

    # Обновляем список
    user_selected_weekdays[user_id] = selected_days

    # Показываем какие дни выбраны
    days_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    selected_days_text = ", ".join([days_names[d-1] for d in sorted(selected_days)])

    if selected_days:
        await callback.message.edit_text(
            f"📅 <b>Выбранные дни:</b> {selected_days_text}\n\n"
            f"<b>Продолжайте выбирать дни или нажмите '✅ Готово':</b>",
            reply_markup=get_weekday_selection_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "📅 <b>Выберите дни недели для повторения:</b>\n"
            "<i>Можно выбрать несколько дней</i>",
            reply_markup=get_weekday_selection_keyboard(),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "weekday_selection_done")
async def weekday_selection_done_handler(callback: CallbackQuery, state: FSMContext):
    """Завершение выбора дней недели"""
    user_id = callback.from_user.id
    selected_days = user_selected_weekdays.get(user_id, [])

    if not selected_days:
        await callback.answer("❌ Выберите хотя бы один день!")
        return

    # Получаем все данные из состояния
    data = await state.get_data()
    recurrence_type = data.get("recurrence_type", "weekly")

    # Сохраняем выбранные дни как recurrence_rule
    recurrence_rule = f"weekly:{','.join(map(str, sorted(selected_days)))}"

    await save_event(callback, data, recurrence_type, state, recurrence_rule)


async def save_event(callback, data, recurrence_type, state, recurrence_rule=None):
    """Сохранение события в базу данных"""
    user_id = callback.from_user.id

    # Определяем параметры повторяемости
    is_recurring = recurrence_type != "none"

    if not recurrence_rule:
        recurrence_rule = recurrence_type if recurrence_type != "none" else None

    # Сохраняем событие в базу данных
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO events (user_id, title, description, event_datetime, location, is_recurring, recurrence_rule)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                data["title"],
                data.get("description"),
                data["event_datetime"],
                data.get("location"),
                is_recurring,
                recurrence_rule
            )
        )
        conn.commit()

        response = "✅ <b>Событие успешно добавлено!</b>\n\n"
        response += f"<b>Название:</b> {data['title']}\n"

        if data.get("description"):
            response += f"<b>Описание:</b> {data['description']}\n"

        response += f"<b>Дата и время:</b> {data['event_datetime']}\n"

        if data.get("location"):
            response += f"<b>Место:</b> {data['location']}\n"

        recurrence_texts = {
            "none": "Не повторяется",
            "daily": "Ежедневно",
            "weekly": "Еженедельно",
            "monthly": "Ежемесячно",
            "yearly": "Ежегодно"
        }
        response += f"<b>Повторяемость:</b> {recurrence_texts.get(recurrence_type, recurrence_type)}\n"

        await callback.message.answer(response, parse_mode="HTML")

        # Показываем кнопку для возврата к списку событий
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Вернуться к событиям", callback_data="back_to_events")]
        ])

        await callback.message.answer(
            "<b>Нажмите кнопку чтобы вернуться к событиям:</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    except Exception as e:
        await callback.message.answer(
            f"❌ <b>Ошибка при сохранении события:</b>\n{str(e)}",
            parse_mode="HTML"
        )

    finally:
        conn.close()
        # Очищаем временные данные
        if user_id in user_selected_weekdays:
            del user_selected_weekdays[user_id]
        await state.clear()


# ==================== ОБРАБОТКА ДЕТАЛЕЙ, РЕДАКТИРОВАНИЯ И УДАЛЕНИЯ СОБЫТИЙ ====================

@router.callback_query(F.data.startswith("view_event_"))
async def view_event_handler(callback: CallbackQuery):
    """Показать детали события"""
    event_id = int(callback.data.split("_")[2])
    await show_event_details(callback, event_id)


@router.callback_query(F.data.startswith("edit_event_"))
async def edit_event_selected(callback: CallbackQuery):
    """Выбрано событие для редактирования"""
    event_id = int(callback.data.split("_")[2])
    await callback.answer()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = dict(cursor.fetchone())
    conn.close()

    if not event:
        await callback.message.answer("❌ Событие не найдено!")
        return

    # Показываем информацию о событии и кнопки редактирования
    response = f"✏️ <b>Редактирование события:</b>\n\n"
    response += f"📝 <b>Название:</b> {event['title']}\n"

    if event['description']:
        response += f"📄 <b>Описание:</b> {event['description']}\n"

    response += f"📅 <b>Дата и время:</b> {event['event_datetime']}\n"

    if event['location']:
        response += f"📍 <b>Место:</b> {event['location']}\n"

    if event['is_recurring']:
        response += f"🔄 <b>Повторяемость:</b> {event['recurrence_rule']}\n"

    response += "\n<b>Выберите что изменить:</b>"

    await callback.message.edit_text(response, parse_mode="HTML")
    await callback.message.edit_reply_markup(reply_markup=get_edit_event_keyboard(event_id))


@router.callback_query(F.data.startswith("delete_event_"))
async def delete_event_selected(callback: CallbackQuery):
    """Выбрано событие для удаления"""
    event_id = int(callback.data.split("_")[2])
    await callback.answer()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = dict(cursor.fetchone())
    conn.close()

    if not event:
        await callback.message.answer("❌ Событие не найдено!")
        return

    # Показываем информацию о событии и кнопку подтверждения
    response = f"🗑️ <b>Удаление события:</b>\n\n"
    response += f"📝 <b>Название:</b> {event['title']}\n"

    if event['description']:
        response += f"📄 <b>Описание:</b> {event['description']}\n"

    response += f"📅 <b>Дата и время:</b> {event['event_datetime']}\n"

    if event['location']:
        response += f"📍 <b>Место:</b> {event['location']}\n"

    response += "\n<b>Вы действительно хотите удалить это событие?</b>"

    await callback.message.edit_text(response, parse_mode="HTML")
    await callback.message.edit_reply_markup(reply_markup=get_delete_event_confirmation_keyboard(event_id))


@router.callback_query(F.data.startswith("confirm_delete_event_"))
async def confirm_delete_event(callback: CallbackQuery):
    """Подтверждение удаления события"""
    event_id = int(callback.data.split("_")[3])

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

    await callback.answer("✅ Событие удалено!")
    await callback.message.edit_text(
        "✅ <b>Событие успешно удалено!</b>\n\nНажмите кнопку чтобы вернуться к событиям:",
        parse_mode="HTML"
    )

    # Кнопка для возврата к событиям
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Вернуться к событиям", callback_data="back_to_events")]
    ])
    await callback.message.edit_reply_markup(reply_markup=keyboard)


@router.callback_query(F.data.startswith("edit_event_field_"))
async def edit_event_field_selected(callback: CallbackQuery, state: FSMContext):
    """Выбрано поле события для редактирования"""
    data_parts = callback.data.split("_")
    field_name = data_parts[3]
    event_id = int(data_parts[4])

    await callback.answer()

    # Сохраняем информацию в состоянии
    await state.update_data(event_id=event_id, field_name=field_name)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = dict(cursor.fetchone())
    conn.close()

    if field_name == "recurrence":
        await callback.message.edit_text("🔄 <b>Выберите новую повторяемость события:</b>", parse_mode="HTML")
        await callback.message.edit_reply_markup(reply_markup=get_recurrence_keyboard(for_edit=True, event_id=event_id))
    else:
        field_names = {
            "title": "название события",
            "description": "описание события (или 'нет' если не нужно)",
            "datetime": "дату и время события (формат: ГГГГ-ММ-ДД ЧЧ:ММ)",
            "location": "место проведения события (или 'нет')"
        }

        current_value = event.get(field_name, "")

        await callback.message.edit_text(
            f"✏️ <b>Редактирование {field_names[field_name]}</b>\n\n"
            f"Текущее значение: <code>{current_value if current_value else 'не указано'}</code>\n\n"
            f"<b>Введите новое значение:</b>",
            parse_mode="HTML"
        )
        await callback.message.edit_reply_markup(reply_markup=None)

        await state.set_state(EditEventStates.waiting_for_field_value)


@router.callback_query(F.data.startswith("select_recurrence_"))
async def select_new_recurrence(callback: CallbackQuery, state: FSMContext):
    """Выбрана новая повторяемость для редактирования"""
    data_parts = callback.data.split("_")
    new_recurrence = data_parts[2]
    event_id = int(data_parts[3])

    await callback.answer(f"Выбрано: {new_recurrence}")

    conn = get_connection()
    cursor = conn.cursor()

    is_recurring = new_recurrence != "none"
    recurrence_rule = new_recurrence if new_recurrence != "none" else None

    cursor.execute(
        "UPDATE events SET is_recurring = ?, recurrence_rule = ? WHERE id = ?",
        (is_recurring, recurrence_rule, event_id)
    )
    conn.commit()
    conn.close()

    await callback.message.edit_text(
        f"✅ <b>Повторяемость события обновлена!</b>",
        parse_mode="HTML"
    )

    # Показываем кнопку для возврата к событию
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Вернуться к событию", callback_data=f"back_to_event_{event_id}")]
    ])
    await callback.message.edit_reply_markup(reply_markup=keyboard)

    await state.clear()


@router.message(EditEventStates.waiting_for_field_value)
async def process_event_field_value(message: Message, state: FSMContext):
    """Обработка нового значения поля события"""
    data = await state.get_data()
    event_id = data['event_id']
    field_name = data['field_name']
    new_value = message.text.strip()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        if field_name == "datetime":
            # Проверяем формат даты и времени
            try:
                datetime.strptime(new_value, '%Y-%m-%d %H:%M')
            except ValueError:
                await message.answer(
                    "❌ <b>Неверный формат даты и времени!</b>\n"
                    "Используйте формат: ГГГГ-ММ-ДД ЧЧ:ММ\n"
                    "Пример: 2024-12-31 18:30",
                    parse_mode="HTML"
                )
                return
        else:
            if new_value.lower() == "нет" or not new_value:
                new_value = None

        if field_name == "title":
            cursor.execute("UPDATE events SET title = ? WHERE id = ?", (new_value, event_id))
        elif field_name == "description":
            cursor.execute("UPDATE events SET description = ? WHERE id = ?", (new_value, event_id))
        elif field_name == "datetime":
            cursor.execute("UPDATE events SET event_datetime = ? WHERE id = ?", (new_value, event_id))
        elif field_name == "location":
            cursor.execute("UPDATE events SET location = ? WHERE id = ?", (new_value, event_id))

        conn.commit()

        field_display_names = {
            "title": "Название события",
            "description": "Описание события",
            "datetime": "Дата и время события",
            "location": "Место проведения события"
        }

        await message.answer(
            f"✅ <b>{field_display_names[field_name]} успешно обновлено!</b>",
            parse_mode="HTML"
        )

        # После обновления возвращаемся к деталям события
        await show_event_details(message, event_id)

    except Exception as e:
        await message.answer(f"❌ <b>Ошибка при обновлении:</b>\n{str(e)}", parse_mode="HTML")
    finally:
        conn.close()
        await state.clear()


@router.callback_query(F.data.startswith("back_to_event_"))
async def back_to_event(callback: CallbackQuery):
    """Вернуться к деталям события"""
    event_id = int(callback.data.split("_")[3])
    await show_event_details(callback, event_id)


@router.callback_query(F.data.startswith("events_page_"))
async def events_page_handler(callback: CallbackQuery):
    """Обработка переключения страниц событий"""
    start_index = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    events = user_events_cache.get(user_id, [])

    if not events:
        await callback.answer("❌ Список событий пуст!")
        return

    response = "🎯 <b>Ваши ближайшие события:</b>\n\n"
    response += "<i>Выберите событие для просмотра деталей:</i>\n\n"

    for i, event in enumerate(events[start_index:start_index+5], 1):
        title = event['title']
        event_datetime = event['event_datetime']

        # Форматируем дату и время
        try:
            dt = datetime.strptime(event_datetime, '%Y-%m-%d %H:%M')
            formatted_date = dt.strftime('%d.%m.%Y %H:%M')
        except:
            formatted_date = event_datetime

        response += f"<b>{start_index + i}.</b> {formatted_date} - {title}\n"

        if event['is_recurring']:
            response += "🔄 <i>Повторяющееся</i>\n"

        response += "\n"

    await callback.message.edit_text(
        response,
        parse_mode="HTML",
    )
    await callback.message.edit_reply_markup(reply_markup=get_events_selection_keyboard(events, start_index))
    await callback.answer()


@router.callback_query(F.data == "back_to_events")
async def back_to_events_handler(callback: CallbackQuery):
    """Вернуться к списку событий"""
    await callback.answer()

    user_id = callback.from_user.id
    user_current_section[user_id] = "events"

    conn = get_connection()
    cursor = conn.cursor()

    # Получаем ближайшие события
    cursor.execute(
        """
        SELECT id, title, description, event_datetime, location, is_recurring, recurrence_rule
        FROM events
        WHERE user_id = ?
        ORDER BY event_datetime
        LIMIT 20
        """,
        (user_id,)
    )

    events = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Сохраняем события в кэш
    user_events_cache[user_id] = events

    if not events:
        response = "🎯 <b>У вас пока нет событий!</b>\n\n"
        response += "Добавьте первое событие с помощью кнопки ниже:"

        await callback.message.edit_text(
            response,
            parse_mode="HTML",
        )
        await callback.message.edit_reply_markup(reply_markup=get_events_list_keyboard())
    else:
        response = "🎯 <b>Ваши ближайшие события:</b>\n\n"
        response += "<i>Выберите событие для просмотра деталей:</i>\n\n"

        for i, event in enumerate(events[:5], 1):
            title = event['title']
            event_datetime = event['event_datetime']

            # Форматируем дату и время
            try:
                dt = datetime.strptime(event_datetime, '%Y-%m-%d %H:%M')
                formatted_date = dt.strftime('%d.%m.%Y %H:%M')
            except:
                formatted_date = event_datetime

            response += f"<b>{i}.</b> {formatted_date} - {title}\n"

            if event['is_recurring']:
                response += "🔄 <i>Повторяющееся</i>\n"

            response += "\n"

        await callback.message.edit_text(
            response,
            parse_mode="HTML",
        )
        await callback.message.edit_reply_markup(reply_markup=get_events_selection_keyboard(events))
