# src/handlers/events/add.py
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.states import AddEventStates

router = Router()


@router.callback_query(F.data == "add_event_btn")
async def add_event_handler(callback: CallbackQuery, state: FSMContext):
    """Начать процесс добавления события"""

    await callback.message.delete()
    await callback.message.answer(
        "🎯 <b>Добавление нового события</b>\n\n"
        "📝 <b>Введите название события:</b>\n"
        "<i>Например: Встреча с друзьями, Концерт, Экзамен</i>",
        parse_mode="HTML",
    )

    await state.set_state(AddEventStates.waiting_for_title)
    await callback.answer()


@router.message(AddEventStates.waiting_for_title)
async def process_event_title(message: Message, state: FSMContext):
    """Обработка названия события"""
    from src.handlers.events.base import validate_event_title

    title = message.text.strip()
    is_valid, error = validate_event_title(title)

    if not is_valid:
        await message.answer(f"❌ {error}", parse_mode="HTML")
        return

    await state.update_data(title=title)
    await message.answer(
        "✅ <b>Название сохранено!</b>\n\n"
        "📄 <b>Теперь введите описание события:</b>\n"
        "<i>Можно подробно описать событие, или напишите 'нет'</i>",
        parse_mode="HTML",
    )

    await state.set_state(AddEventStates.waiting_for_description)


@router.message(AddEventStates.waiting_for_description)
async def process_event_description(message: Message, state: FSMContext):
    """Обработка описания события"""
    from src.handlers.events.base import validate_description

    description = message.text.strip()
    is_valid, error = validate_description(description)

    if not is_valid:
        await message.answer(f"❌ {error}", parse_mode="HTML")
        return

    # Обработка "нет"
    if description.lower() == "нет":
        description = None

    await state.update_data(description=description)
    await message.answer(
        f"✅ <b>Описание сохранено: {description if description else 'не указано'}</b>\n\n"
        "📅 <b>Теперь введите дату и время события:</b>\n"
        "<i>Формат: ГГГГ-ММ-ДД ЧЧ:ММ (пример: 2024-12-31 18:30)</i>",
        parse_mode="HTML",
    )

    await state.set_state(AddEventStates.waiting_for_datetime)


@router.message(AddEventStates.waiting_for_datetime)
async def process_event_datetime(message: Message, state: FSMContext):
    """Обработка даты и времени события"""
    from src.handlers.events.base import validate_datetime

    datetime_str = message.text.strip()
    is_valid, error, event_datetime = validate_datetime(datetime_str)

    if not is_valid:
        await message.answer(f"❌ {error}", parse_mode="HTML")
        return

    await state.update_data(event_datetime=event_datetime)

    formatted_time = event_datetime.strftime("%d.%m.%Y %H:%M")
    await message.answer(
        f"✅ <b>Дата и время сохранены: {formatted_time}</b>\n\n"
        "📍 <b>Введите место проведения события:</b>\n"
        "<i>Например: Кафе 'Уютное место', или напишите 'нет'</i>",
        parse_mode="HTML",
    )

    await state.set_state(AddEventStates.waiting_for_location)


@router.message(AddEventStates.waiting_for_location)
async def process_event_location(message: Message, state: FSMContext):
    """Обработка места проведения события"""
    from src.handlers.events.base import validate_location
    from src.keyboards import get_recurrence_keyboard

    location = message.text.strip()
    is_valid, error = validate_location(location)

    if not is_valid:
        await message.answer(f"❌ {error}", parse_mode="HTML")
        return

    # Обработка "нет"
    if location.lower() == "нет":
        location = None

    await state.update_data(location=location)

    location_text = location if location else "не указано"
    await message.answer(
        f"✅ <b>Место сохранено: {location_text}</b>\n\n"
        "🔄 <b>Выберите повторяемость события:</b>",
        reply_markup=get_recurrence_keyboard(),
        parse_mode="HTML",
    )

    await state.set_state(AddEventStates.waiting_for_recurrence)


@router.callback_query(
    AddEventStates.waiting_for_recurrence, F.data.startswith("select_recurrence_")
)
async def process_event_recurrence(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора повторяемости"""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from src.handlers.events.base import save_event

    recurrence_type = callback.data.replace("select_recurrence_", "")

    # Преобразуем в удобочитаемый текст
    recurrence_text = {
        "none": "❌ Не повторяется",
        "daily": "📅 Ежедневно",
        "weekly": "📅 Еженедельно",
        "monthly": "📅 Ежемесячно",
        "yearly": "📅 Ежегодно",
    }.get(recurrence_type, recurrence_type)

    # Определяем, повторяющееся ли событие
    is_recurring = recurrence_type != "none"

    await state.update_data(recurrence_rule=recurrence_type, is_recurring=is_recurring)

    # Получаем все данные
    data = await state.get_data()
    user_id = callback.from_user.id

    # Сохраняем событие
    success, event_id, msg = save_event(user_id, data)

    if success:
        # Формируем ответ
        response = "🎉 <b>Событие успешно добавлено!</b>\n\n"
        response += f"📝 <b>Название:</b> {data['title']}\n"

        # Форматируем дату
        event_dt = data["event_datetime"]
        formatted_time = event_dt.strftime("%d.%m.%Y %H:%M")
        response += f"📅 <b>Дата и время:</b> {formatted_time}\n"

        if data.get("location"):
            response += f"📍 <b>Место:</b> {data['location']}\n"
        if data.get("description"):
            desc_preview = data["description"][:100] + (
                "..." if len(data["description"]) > 100 else ""
            )
            response += f"📄 <b>Описание:</b> {desc_preview}\n"

        response += f"🔄 <b>Повторяемость:</b> {recurrence_text}\n"

        # Кнопка возврата
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
        await callback.message.answer(f"❌ <b>Ошибка:</b> {msg}", parse_mode="HTML")

    # Очищаем состояние
    await state.clear()
    await callback.answer(f"Выбрано: {recurrence_text}")
