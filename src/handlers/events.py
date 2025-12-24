# src/handlers/events.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from database import get_connection
from keyboard import (
    get_event_actions_keyboard,
    get_edit_event_keyboard,
    create_inline_keyboard_from_list,
    get_main_keyboard
)

router = Router()

class EventStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_date = State()
    waiting_for_time = State()
    editing_field = State()

# ==================== ФУНКЦИИ ДЛЯ ВЫЗОВА ИЗ BOT.PY ====================

async def show_events_from_bot(message: Message):
    """Показать события (для вызова из bot.py)"""
    await show_events_internal(message)

async def add_event_command_from_bot(message: Message, state: FSMContext):
    """Добавить событие (для вызова из bot.py)"""
    await add_event_command_internal(message, state)

async def show_upcoming_events_from_bot(message: Message):
    """Показать ближайшие события (для вызова из bot.py)"""
    await show_upcoming_events_internal(message)

# ==================== ВНУТРЕННИЕ ФУНКЦИИ ====================

async def show_events_internal(message: Message):
    """Показать события (внутренняя функция)"""
    user_id = message.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, event_date, event_time FROM events WHERE user_id = ? ORDER BY event_date ASC', (user_id,))
    events = cursor.fetchall()
    conn.close()
    
    if not events:
        await message.answer("📅 <b>Нет событий!</b>", parse_mode="HTML")
        return
    
    response = "🎯 <b>Ваши события:</b>\n\n"
    today = datetime.now().date()
    
    for event_id, title, event_date, event_time in events:
        try:
            event_datetime = datetime.strptime(event_date, "%Y-%m-%d")
            days_until = (event_datetime.date() - today).days
            
            time_str = f" в {event_time}" if event_time else ""
            
            if days_until < 0:
                status = "🕐 Прошло:"
            elif days_until == 0:
                status = "🔥 Сегодня!"
            elif days_until <= 3:
                status = f"⚠️ Через {days_until} дн.:"
            else:
                status = f"📅 Через {days_until} дн.:"
            
            response += f"{status} {title} - {event_date}{time_str}\n"
        except:
            response += f"📅 {title} - {event_date}\n"
    
    keyboard = get_event_actions_keyboard()
    
    await message.answer(response, reply_markup=keyboard, parse_mode="HTML")

async def add_event_command_internal(message: Message, state: FSMContext):
    """Добавить событие (внутренняя функция)"""
    await message.answer("🎯 <b>Введите название события:</b>", parse_mode="HTML")
    await state.set_state(EventStates.waiting_for_title)

async def show_upcoming_events_internal(message: Message):
    """Показать ближайшие события (внутренняя функция)"""
    user_id = message.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT title, event_date, event_time 
        FROM events 
        WHERE user_id = ? 
        AND date(event_date) >= date('now')
        ORDER BY event_date ASC
        LIMIT 10
    ''', (user_id,))
    
    events = cursor.fetchall()
    conn.close()
    
    if not events:
        await message.answer("📭 <b>Нет предстоящих событий!</b>", parse_mode="HTML")
        return
    
    today = datetime.now().date()
    
    response = "🔔 <b>Ближайшие события:</b>\n\n"
    for title, event_date, event_time in events:
        try:
            event_datetime = datetime.strptime(event_date, "%Y-%m-%d")
            days_until = (event_datetime.date() - today).days
            time_str = f" в {event_time}" if event_time else ""
            
            if days_until == 0:
                response += f"🔥 <b>Сегодня!</b> {title}{time_str}\n"
            elif days_until == 1:
                response += f"⚠️ <b>Завтра!</b> {title}{time_str}\n"
            elif days_until <= 7:
                response += f"📅 Через {days_until} дней: {title}{time_str}\n"
            else:
                response += f"📅 {event_date}{time_str}: {title}\n"
        except:
            response += f"📅 {event_date}: {title}\n"
    
    await message.answer(response, parse_mode="HTML")

# ==================== КОМАНДЫ ДЛЯ СОБЫТИЙ ====================

@router.message(Command("events"))
async def cmd_events(message: Message):
    """Команда /events"""
    await show_events_internal(message)

@router.message(Command("add_event"))
async def cmd_add_event(message: Message, state: FSMContext):
    """Команда /add_event"""
    await add_event_command_internal(message, state)

@router.message(Command("upcoming"))
async def cmd_upcoming(message: Message):
    """Команда /upcoming - ближайшие события"""
    await show_upcoming_events_internal(message)

@router.message(EventStates.waiting_for_title)
async def process_event_title(message: Message, state: FSMContext):
    """Обработка названия события"""
    await state.update_data(title=message.text)
    await message.answer("📅 <b>Введите дату события (ГГГГ-ММ-ДД):</b>", parse_mode="HTML")
    await state.set_state(EventStates.waiting_for_date)

@router.message(EventStates.waiting_for_date)
async def process_event_date(message: Message, state: FSMContext):
    """Обработка даты события"""
    date_str = message.text.strip()
    
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        await state.update_data(event_date=date_str)
        await message.answer("⏰ <b>Введите время события (ЧЧ:ММ) или 'нет':</b>", parse_mode="HTML")
        await state.set_state(EventStates.waiting_for_time)
        
    except ValueError:
        await message.answer("❌ <b>Неверный формат!</b> Используйте ГГГГ-ММ-ДД:", parse_mode="HTML")
        return

@router.message(EventStates.waiting_for_time)
async def process_event_time(message: Message, state: FSMContext):
    """Обработка времени события"""
    time_str = message.text.strip()
    
    if time_str.lower() == 'нет' or time_str == '':
        time_str = None
    else:
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            await message.answer("❌ <b>Неверный формат времени!</b> Используйте ЧЧ:ММ или 'нет':", parse_mode="HTML")
            return
    
    data = await state.get_data()
    title = data.get('title')
    event_date = data.get('event_date')
    user_id = message.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO events (user_id, title, event_date, event_time) VALUES (?, ?, ?, ?)', 
                   (user_id, title, event_date, time_str))
    conn.commit()
    conn.close()
    
    time_info = f" в {time_str}" if time_str else ""
    await message.answer(f"✅ <b>Событие '{title}' на {event_date}{time_info} добавлено!</b>", parse_mode="HTML")
    await state.clear()

# ==================== INLINE КНОПКИ ДЛЯ СОБЫТИЙ ====================

@router.callback_query(F.data == "delete_event_menu")
async def delete_event_menu(callback: CallbackQuery):
    """Меню удаления событий"""
    user_id = callback.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, event_date 
        FROM events 
        WHERE user_id = ? 
        ORDER BY event_date ASC
    ''', (user_id,))
    
    events = cursor.fetchall()
    conn.close()
    
    if not events:
        await callback.message.answer("📭 <b>Нет событий для удаления!</b>", parse_mode="HTML")
        await callback.answer()
        return
    
    items = []
    for event_id, title, event_date in events:
        button_text = f"{title} ({event_date})"
        items.append((event_id, button_text))
    
    keyboard = create_inline_keyboard_from_list(
        items=items,
        callback_prefix="delete_event",
        back_callback="back_to_events"
    )
    
    await callback.message.edit_text(
        "🗑️ <b>Выберите событие для удаления:</b>\n\n"
        "<i>Нажмите на событие, чтобы удалить его:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("delete_event_"))
async def process_delete_event(callback: CallbackQuery):
    """Обработка удаления события"""
    event_id = int(callback.data.split("_")[2])
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT title, event_date FROM events WHERE id = ?', (event_id,))
    event_info = cursor.fetchone()
    
    if event_info:
        title, event_date = event_info
        cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
        conn.commit()
        
        await callback.message.edit_text(f"🗑️ <b>Событие '{title}' ({event_date}) удалено!</b>", parse_mode="HTML")
    else:
        await callback.message.edit_text("❌ <b>Событие не найден!</b>", parse_mode="HTML")
    
    conn.close()
    await callback.answer()

@router.callback_query(F.data == "edit_event_menu")
async def edit_event_menu(callback: CallbackQuery):
    """Меню редактирования событий"""
    user_id = callback.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, event_date 
        FROM events 
        WHERE user_id = ? 
        ORDER BY event_date ASC
    ''', (user_id,))
    
    events = cursor.fetchall()
    conn.close()
    
    if not events:
        await callback.message.answer("📭 <b>Нет событий для редактирования!</b>", parse_mode="HTML")
        await callback.answer()
        return
    
    items = []
    for event_id, title, event_date in events:
        button_text = f"{title} ({event_date})"
        items.append((event_id, button_text))
    
    keyboard = create_inline_keyboard_from_list(
        items=items,
        callback_prefix="edit_event",
        back_callback="back_to_events"
    )
    
    await callback.message.edit_text(
        "✏️ <b>Выберите событие для редактирования:</b>\n\n"
        "<i>Нажмите на событие, чтобы изменить его:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_event_"))
async def edit_event_choice(callback: CallbackQuery):
    """Выбор параметра для редактирования события"""
    event_id = int(callback.data.split("_")[2])
    
    keyboard = get_edit_event_keyboard(event_id)
    
    await callback.message.edit_text(
        "✏️ <b>Что вы хотите изменить в событии?</b>\n\n"
        "<i>Выберите параметр для редактирования:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_events")
async def back_to_events(callback: CallbackQuery):
    """Вернуться к списку событий"""
    await show_events_internal(callback.message)
    await callback.answer()

# ==================== ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ СОБЫТИЙ ====================

@router.callback_query(F.data.startswith("edit_event_title_"))
async def edit_event_title_handler(callback: CallbackQuery, state: FSMContext):
    """Редактирование названия события"""
    event_id = int(callback.data.split("_")[3])
    await state.update_data(edit_event_id=event_id, edit_field="title")
    await callback.message.answer("🎯 <b>Введите новое название события:</b>", parse_mode="HTML")
    await state.set_state(EventStates.editing_field)
    await callback.answer()

@router.callback_query(F.data.startswith("edit_event_date_"))
async def edit_event_date_handler(callback: CallbackQuery, state: FSMContext):
    """Редактирование даты события"""
    event_id = int(callback.data.split("_")[3])
    await state.update_data(edit_event_id=event_id, edit_field="date")
    await callback.message.answer("📅 <b>Введите новую дату события (ГГГГ-ММ-ДД):</b>", parse_mode="HTML")
    await state.set_state(EventStates.editing_field)
    await callback.answer()

@router.callback_query(F.data.startswith("edit_event_time_"))
async def edit_event_time_handler(callback: CallbackQuery, state: FSMContext):
    """Редактирование времени события"""
    event_id = int(callback.data.split("_")[3])
    await state.update_data(edit_event_id=event_id, edit_field="time")
    await callback.message.answer("⏰ <b>Введите новое время события (ЧЧ:ММ) или 'нет':</b>", parse_mode="HTML")
    await state.set_state(EventStates.editing_field)
    await callback.answer()

@router.message(EventStates.editing_field)
async def process_event_edit_field(message: Message, state: FSMContext):
    """Обработка редактирования поля события"""
    data = await state.get_data()
    
    if 'edit_event_id' not in data or 'edit_field' not in data:
        await message.answer("❌ <b>Ошибка редактирования.</b> Попробуйте снова.", parse_mode="HTML")
        await state.clear()
        return
    
    event_id = data['edit_event_id']
    field = data['edit_field']
    new_value = message.text.strip()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT title, event_date FROM events WHERE id = ?', (event_id,))
    event_info = cursor.fetchone()
    
    if not event_info:
        await message.answer("❌ <b>Событие не найдено!</b>", parse_mode="HTML")
        await state.clear()
        conn.close()
        return
    
    field_updated = False
    field_name = ""
    
    if field == "title":
        cursor.execute('UPDATE events SET title = ? WHERE id = ?', (new_value, event_id))
        field_name = "название"
        field_updated = True
    elif field == "date":
        try:
            datetime.strptime(new_value, "%Y-%m-%d")
            cursor.execute('UPDATE events SET event_date = ? WHERE id = ?', (new_value, event_id))
            field_name = "дата"
            field_updated = True
        except ValueError:
            await message.answer("❌ <b>Неверный формат даты!</b> Используйте ГГГГ-ММ-ДД", parse_mode="HTML")
    elif field == "time":
        if new_value.lower() == 'нет':
            new_value = None
        else:
            try:
                datetime.strptime(new_value, "%H:%M")
            except ValueError:
                await message.answer("❌ <b>Неверный формат времени!</b> Используйте ЧЧ:ММ", parse_mode="HTML")
                conn.close()
                return
        cursor.execute('UPDATE events SET event_time = ? WHERE id = ?', (new_value, event_id))
        field_name = "время"
        field_updated = True
    
    if field_updated:
        conn.commit()
        title, event_date = event_info
        
        await message.answer(
            f"✅ <b>{field_name.capitalize()} успешно обновлено!</b>\n\n"
            f"Событие '{title}' ({event_date}) изменено.",
            parse_mode="HTML"
        )
        
        await show_events_internal(message)
    else:
        await message.answer("❌ <b>Не удалось обновить поле.</b> Попробуйте еще раз.", parse_mode="HTML")
    
    conn.close()
    await state.clear()