# src/handlers/tasks.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from database import get_connection, format_deadline
from keyboard import (
    get_task_actions_keyboard,
    create_inline_keyboard_from_list,
    get_main_keyboard
)

router = Router()

class TaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_deadline = State()
    editing_field = State()

# ==================== ФУНКЦИИ ДЛЯ ВЫЗОВА ИЗ BOT.PY ====================

async def show_tasks_from_bot(message: Message):
    """Показать задачи (для вызова из bot.py)"""
    await show_tasks_internal(message)

async def add_task_command_from_bot(message: Message, state: FSMContext):
    """Добавить задачу (для вызова из bot.py)"""
    await add_task_command_internal(message, state)

# ==================== ВНУТРЕННИЕ ФУНКЦИИ ====================

async def show_tasks_internal(message: Message):
    """Показать все задачи пользователя (внутренняя функция)"""
    user_id = message.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, deadline, is_completed, created_at 
        FROM tasks 
        WHERE user_id = ? AND is_completed = FALSE
        ORDER BY deadline ASC
    ''', (user_id,))
    
    tasks = cursor.fetchall()
    conn.close()
    
    if not tasks:
        await message.answer("📋 <b>У вас нет активных задач!</b>", parse_mode="HTML")
        return
    
    response = "📋 <b>Ваши задачи:</b>\n\n"
    urgent_count = 0
    
    for task in tasks:
        task_id, title, deadline, is_completed, created_at = task
        deadline_text = format_deadline(deadline)
        
        if deadline:
            try:
                deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
                days_left = (deadline_date.date() - datetime.now().date()).days
                if 0 <= days_left < 7:
                    response += f"🔥 <b>{title}</b> (до {deadline_text})\n"
                    urgent_count += 1
                    continue
            except:
                pass
        
        response += f"• {title} (до {deadline_text})\n"
    
    if urgent_count > 0:
        response = f"⚠️ <b>У вас {urgent_count} срочных задач!</b>\n\n" + response
    
    keyboard = get_task_actions_keyboard()
    
    await message.answer(response, reply_markup=keyboard, parse_mode="HTML")

async def add_task_command_internal(message: Message, state: FSMContext):
    """Начало добавления задачи (внутренняя функция)"""
    await message.answer("📝 <b>Введите название задачи:</b>", parse_mode="HTML")
    await state.set_state(TaskStates.waiting_for_title)

# ==================== КОМАНДЫ ДЛЯ ЗАДАЧ ====================

@router.message(Command("tasks"))
async def cmd_tasks(message: Message):
    """Команда /tasks"""
    await show_tasks_internal(message)

@router.message(Command("add_task"))
async def cmd_add_task(message: Message, state: FSMContext):
    """Команда /add_task"""
    await add_task_command_internal(message, state)

@router.message(TaskStates.waiting_for_title)
async def process_task_title(message: Message, state: FSMContext):
    """Обработка названия задачи"""
    await state.update_data(title=message.text)
    await message.answer("📅 <b>Введите дедлайн (ГГГГ-ММ-ДД) или 'нет':</b>", parse_mode="HTML")
    await state.set_state(TaskStates.waiting_for_deadline)

@router.message(TaskStates.waiting_for_deadline)
async def process_task_deadline(message: Message, state: FSMContext):
    """Обработка дедлайна задачи"""
    deadline = message.text.strip()
    
    if deadline.lower() == 'нет' or deadline == '':
        deadline = None
    else:
        try:
            datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            await message.answer("❌ <b>Неверный формат!</b> Используйте ГГГГ-ММ-ДД или 'нет':", parse_mode="HTML")
            return
    
    data = await state.get_data()
    title = data.get('title')
    user_id = message.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tasks (user_id, title, deadline) VALUES (?, ?, ?)', 
                   (user_id, title, deadline))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ <b>Задача '{title}' добавлена!</b>", parse_mode="HTML")
    await state.clear()

@router.message(Command("urgent_tasks"))
async def cmd_urgent_tasks(message: Message):
    """Показать только срочные задачи"""
    user_id = message.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT title, deadline 
        FROM tasks 
        WHERE user_id = ? AND is_completed = FALSE AND deadline IS NOT NULL
        ORDER BY deadline ASC
    ''', (user_id,))
    
    tasks = cursor.fetchall()
    conn.close()
    
    response = "🔥 <b>Срочные задачи:</b>\n\n"
    urgent_count = 0
    
    for title, deadline in tasks:
        try:
            deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
            days_left = (deadline_date.date() - datetime.now().date()).days
            if 0 <= days_left < 7:
                deadline_text = format_deadline(deadline)
                response += f"• {title} (до {deadline_text})\n"
                urgent_count += 1
        except:
            continue
    
    if urgent_count == 0:
        response = "✅ <b>У вас нет срочных задач!</b>"
    
    await message.answer(response, parse_mode="HTML")

# ==================== INLINE КНОПКИ ДЛЯ ЗАДАЧ ====================

@router.callback_query(F.data == "complete_task_menu")
async def complete_task_menu(callback: CallbackQuery):
    """Меню завершения задач"""
    user_id = callback.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, deadline 
        FROM tasks 
        WHERE user_id = ? AND is_completed = FALSE
        ORDER BY deadline ASC
    ''', (user_id,))
    
    tasks = cursor.fetchall()
    conn.close()
    
    if not tasks:
        await callback.message.answer("📭 <b>Нет активных задач для завершения!</b>", parse_mode="HTML")
        await callback.answer()
        return
    
    items = []
    for task_id, title, deadline in tasks:
        deadline_text = format_deadline(deadline)
        button_text = f"{title} ({deadline_text})"
        items.append((task_id, button_text))
    
    keyboard = create_inline_keyboard_from_list(
        items=items,
        callback_prefix="complete",
        back_callback="back_to_tasks"
    )
    
    await callback.message.edit_text(
        "✅ <b>Выберите задачу для завершения:</b>\n\n"
        "<i>Нажмите на задачу, чтобы отметить её как выполненную:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("complete_"))
async def process_complete_task(callback: CallbackQuery):
    """Обработка завершения задачи"""
    task_id = int(callback.data.split("_")[1])
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT title FROM tasks WHERE id = ?', (task_id,))
    task_info = cursor.fetchone()
    
    if task_info:
        title = task_info[0]
        cursor.execute('UPDATE tasks SET is_completed = TRUE WHERE id = ?', (task_id,))
        conn.commit()
        
        await callback.message.edit_text(f"✅ <b>Задача '{title}' завершена!</b>", parse_mode="HTML")
    else:
        await callback.message.edit_text("❌ <b>Задача не найдена!</b>", parse_mode="HTML")
    
    conn.close()
    await callback.answer()

@router.callback_query(F.data == "delete_task_menu")
async def delete_task_menu(callback: CallbackQuery):
    """Меню удаления задач"""
    user_id = callback.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, deadline 
        FROM tasks 
        WHERE user_id = ? AND is_completed = FALSE
        ORDER BY deadline ASC
    ''', (user_id,))
    
    tasks = cursor.fetchall()
    conn.close()
    
    if not tasks:
        await callback.message.answer("📭 <b>Нет активных задач для удаления!</b>", parse_mode="HTML")
        await callback.answer()
        return
    
    items = []
    for task_id, title, deadline in tasks:
        deadline_text = format_deadline(deadline)
        button_text = f"{title} ({deadline_text})"
        items.append((task_id, button_text))
    
    keyboard = create_inline_keyboard_from_list(
        items=items,
        callback_prefix="delete_task",
        back_callback="back_to_tasks"
    )
    
    await callback.message.edit_text(
        "🗑️ <b>Выберите задачу для удаления:</b>\n\n"
        "<i>Нажмите на задачу, чтобы удалить её:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("delete_task_"))
async def process_delete_task(callback: CallbackQuery):
    """Обработка удаления задачи"""
    task_id = int(callback.data.split("_")[2])
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT title FROM tasks WHERE id = ?', (task_id,))
    task_info = cursor.fetchone()
    
    if task_info:
        title = task_info[0]
        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
        
        await callback.message.edit_text(f"🗑️ <b>Задача '{title}' удалена!</b>", parse_mode="HTML")
    else:
        await callback.message.edit_text("❌ <b>Задача не найдена!</b>", parse_mode="HTML")
    
    conn.close()
    await callback.answer()

@router.callback_query(F.data == "back_to_tasks")
async def back_to_tasks(callback: CallbackQuery):
    """Вернуться к списку задач"""
    await show_tasks_internal(callback.message)
    await callback.answer()