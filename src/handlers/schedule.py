# src/handlers/schedule.py
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
    get_schedule_actions_keyboard,
    get_lesson_detail_actions_keyboard,
    get_edit_lesson_keyboard,
    get_confirmation_keyboard,
    create_inline_keyboard_from_list,
    get_main_keyboard
)

router = Router()

# ==================== СОСТОЯНИЯ ДЛЯ ДОБАВЛЕНИЯ УРОКА ====================

class ScheduleStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_time = State()
    waiting_for_room = State()
    waiting_for_teacher = State()
    editing_field = State()

# ==================== ФУНКЦИИ ДЛЯ ВЫЗОВА ИЗ BOT.PY ====================

async def show_schedule_menu_from_bot(message: Message):
    """Показать меню расписания (для вызова из bot.py)"""
    await show_interactive_schedule(message)

async def start_add_lesson_from_bot(message: Message, state: FSMContext, day: str):
    """Начать добавление урока (для вызова из bot.py)"""
    await state.update_data(day=day)
    await message.answer(
        f"📅 <b>Выбран день:</b> {day}\n\n"
        "📚 <b>Введите название предмета:</b>",
        parse_mode="HTML"
    )
    await state.set_state(ScheduleStates.waiting_for_subject)

# ==================== ИНТЕРАКТИВНОЕ РАСПИСАНИЕ ====================

async def show_interactive_schedule(message: Message):
    """Показать интерактивное расписание с группировкой по дням"""
    user_id = message.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, subject, day_of_week, start_time, end_time, room, teacher
        FROM schedule 
        WHERE user_id = ? 
        ORDER BY 
            CASE day_of_week
                WHEN 'Понедельник' THEN 1
                WHEN 'Вторник' THEN 2
                WHEN 'Среда' THEN 3
                WHEN 'Четверг' THEN 4
                WHEN 'Пятница' THEN 5
                WHEN 'Суббота' THEN 6
                WHEN 'Воскресенье' THEN 7
                ELSE 8
            END,
            start_time
    ''', (user_id,))
    
    schedule = cursor.fetchall()
    conn.close()
    
    if not schedule:
        keyboard = get_schedule_actions_keyboard()
        
        await message.answer(
            "📅 <b>Ваше расписание пусто!</b>\n\n"
            "Начните с добавления первого урока:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    # Группируем уроки по дням недели
    schedule_by_day = {}
    for lesson_id, subject, day, start_time, end_time, room, teacher in schedule:
        if day not in schedule_by_day:
            schedule_by_day[day] = []
        
        schedule_by_day[day].append({
            'id': lesson_id,
            'subject': subject,
            'start_time': start_time,
            'end_time': end_time,
            'room': room,
            'teacher': teacher
        })
    
    # Формируем сообщение с группировкой по дням
    response = "📅 <b>Ваше расписание:</b>\n\n"
    
    days_order = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    
    for day in days_order:
        if day in schedule_by_day:
            response += f"<b>──────── {day} ────────</b>\n"
            
            for i, lesson in enumerate(schedule_by_day[day], 1):
                room_info = f", ауд. {lesson['room']}" if lesson['room'] else ""
                teacher_info = f", {lesson['teacher']}" if lesson['teacher'] else ""
                
                response += f"{i}. <b>{lesson['start_time']}-{lesson['end_time']}</b>: {lesson['subject']}{room_info}{teacher_info}\n"
            
            response += "\n"
    
    keyboard = get_schedule_actions_keyboard()
    
    await message.answer(response, reply_markup=keyboard, parse_mode="HTML")

# ==================== INLINE КНОПКИ ДЛЯ УРОКОВ ====================

@router.callback_query(F.data == "add_lesson")
async def add_lesson_inline(callback: CallbackQuery):
    """Добавить урок через inline-кнопку"""
    from keyboard import get_add_lesson_keyboard
    await callback.message.answer(
        "📝 <b>Добавление нового урока</b>\n\n"
        "Выберите день недели:",
        reply_markup=get_add_lesson_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "view_all_schedule")
async def view_all_schedule_callback(callback: CallbackQuery):
    """Показать все расписание через inline-кнопку"""
    await show_interactive_schedule(callback.message)
    await callback.answer()

@router.callback_query(F.data == "delete_lesson_menu")
async def delete_lesson_menu_inline(callback: CallbackQuery):
    """Меню удаления урока через inline-кнопку"""
    user_id = callback.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, subject, day_of_week, start_time 
        FROM schedule 
        WHERE user_id = ? 
        ORDER BY 
            CASE day_of_week
                WHEN 'Понедельник' THEN 1
                WHEN 'Вторник' THEN 2
                WHEN 'Среда' THEN 3
                WHEN 'Четверг' THEN 4
                WHEN 'Пятница' THEN 5
                WHEN 'Суббота' THEN 6
                WHEN 'Воскресенье' THEN 7
                ELSE 8
            END,
            start_time
    ''', (user_id,))
    
    lessons = cursor.fetchall()
    conn.close()
    
    if not lessons:
        await callback.message.answer("📭 <b>Нет уроков для удаления!</b>", parse_mode="HTML")
        await callback.answer()
        return
    
    items = []
    for lesson_id, subject, day, start_time in lessons:
        button_text = f"{day} {start_time}: {subject}"
        items.append((lesson_id, button_text))
    
    keyboard = create_inline_keyboard_from_list(
        items=items,
        callback_prefix="view_lesson",
        back_callback="back_to_schedule"
    )
    
    await callback.message.edit_text(
        "🗑️ <b>Выберите урок для удаления:</b>\n\n"
        "<i>Нажмите на урок для просмотра и удаления:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "edit_lesson_menu")
async def edit_lesson_menu_main(callback: CallbackQuery):
    """Главное меню редактирования уроков через inline-кнопку"""
    user_id = callback.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, subject, day_of_week, start_time 
        FROM schedule 
        WHERE user_id = ? 
        ORDER BY 
            CASE day_of_week
                WHEN 'Понедельник' THEN 1
                WHEN 'Вторник' THEN 2
                WHEN 'Среда' THEN 3
                WHEN 'Четверг' THEN 4
                WHEN 'Пятница' THEN 5
                WHEN 'Суббота' THEN 6
                WHEN 'Воскресенье' THEN 7
                ELSE 8
            END,
            start_time
    ''', (user_id,))
    
    lessons = cursor.fetchall()
    conn.close()
    
    if not lessons:
        await callback.message.answer("📭 <b>Нет уроков для редактирования!</b>", parse_mode="HTML")
        await callback.answer()
        return
    
    items = []
    for lesson_id, subject, day, start_time in lessons:
        button_text = f"{day} {start_time}: {subject}"
        items.append((lesson_id, button_text))
    
    keyboard = create_inline_keyboard_from_list(
        items=items,
        callback_prefix="edit_lesson",
        back_callback="back_to_schedule"
    )
    
    await callback.message.edit_text(
        "✏️ <b>Выберите урок для редактирования:</b>\n\n"
        "<i>Нажмите на урок для просмотра и редактирования:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("view_lesson_"))
async def view_lesson_details(callback: CallbackQuery):
    """Просмотр деталей урока с кнопками действий"""
    lesson_id = int(callback.data.split("_")[2])
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT subject, day_of_week, start_time, end_time, room, teacher 
        FROM schedule WHERE id = ?
    ''', (lesson_id,))
    
    lesson = cursor.fetchone()
    conn.close()
    
    if not lesson:
        await callback.message.edit_text("❌ <b>Урок не найден!</b>", parse_mode="HTML")
        await callback.answer()
        return
    
    subject, day, start_time, end_time, room, teacher = lesson
    
    room_info = f", ауд. {room}" if room else ""
    teacher_info = f", {teacher}" if teacher else ""
    
    keyboard = get_lesson_detail_actions_keyboard(lesson_id)
    
    await callback.message.edit_text(
        f"📋 <b>Детали урока:</b>\n\n"
        f"• <b>День:</b> {day}\n"
        f"• <b>Время:</b> {start_time}-{end_time}\n"
        f"• <b>Предмет:</b> {subject}\n"
        f"• <b>Аудитория:</b> {room or 'не указана'}\n"
        f"• <b>Преподаватель:</b> {teacher or 'не указан'}\n\n"
        f"<i>Выберите действие:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_lesson_"))
async def edit_lesson_menu_inline(callback: CallbackQuery):
    """Меню редактирования урока через inline-кнопку"""
    lesson_id = int(callback.data.split("_")[2])
    
    keyboard = get_edit_lesson_keyboard(lesson_id)
    
    await callback.message.edit_text(
        "✏️ <b>Что вы хотите изменить в уроке?</b>\n\n"
        "<i>Выберите параметр для редактирования:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_lesson(callback: CallbackQuery):
    """Подтверждение удаления урока"""
    lesson_id = int(callback.data.split("_")[2])
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT subject, day_of_week FROM schedule WHERE id = ?', (lesson_id,))
    lesson_info = cursor.fetchone()
    
    if lesson_info:
        subject, day = lesson_info
        
        keyboard = get_confirmation_keyboard(lesson_id)
        
        await callback.message.edit_text(
            f"⚠️ <b>Вы уверены, что хотите удалить урок?</b>\n\n"
            f"• <b>Предмет:</b> {subject}\n"
            f"• <b>День:</b> {day}\n\n"
            f"<i>Это действие нельзя отменить!</i>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text("❌ <b>Урок не найден!</b>", parse_mode="HTML")
    
    conn.close()
    await callback.answer()

@router.callback_query(F.data.startswith("delete_now_"))
async def delete_lesson_now(callback: CallbackQuery):
    """Удаление урока после подтверждения"""
    lesson_id = int(callback.data.split("_")[2])
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT subject, day_of_week FROM schedule WHERE id = ?', (lesson_id,))
    lesson_info = cursor.fetchone()
    
    if lesson_info:
        subject, day = lesson_info
        cursor.execute('DELETE FROM schedule WHERE id = ?', (lesson_id,))
        conn.commit()
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Вернуться к расписанию", callback_data="back_to_schedule")]
        ])
        
        await callback.message.edit_text(
            f"✅ <b>Урок '{subject}' ({day}) успешно удален!</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text("❌ <b>Урок не найден!</b>", parse_mode="HTML")
    
    conn.close()
    await callback.answer()

@router.callback_query(F.data == "back_to_schedule")
async def back_to_schedule_inline(callback: CallbackQuery):
    """Вернуться к расписанию через inline-кнопку"""
    await show_interactive_schedule(callback.message)
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def back_to_main_inline(callback: CallbackQuery):
    """Вернуться в главное меню через inline-кнопку"""
    await callback.message.answer(
        "📱 <b>Главное меню</b>\n\n"
        "Выберите раздел:",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# ==================== ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ ПОЛЕЙ ====================

@router.callback_query(F.data.startswith("edit_lesson_subject_"))
async def edit_lesson_subject_handler(callback: CallbackQuery, state: FSMContext):
    """Редактирование предмета"""
    lesson_id = int(callback.data.split("_")[3])
    await state.update_data(edit_lesson_id=lesson_id, edit_field="subject")
    await callback.message.answer("📚 <b>Введите новое название предмета:</b>", parse_mode="HTML")
    await state.set_state(ScheduleStates.editing_field)
    await callback.answer()

@router.callback_query(F.data.startswith("edit_lesson_day_"))
async def edit_lesson_day_handler(callback: CallbackQuery, state: FSMContext):
    """Редактирование дня недели"""
    lesson_id = int(callback.data.split("_")[3])
    await state.update_data(edit_lesson_id=lesson_id, edit_field="day")
    await callback.message.answer("📅 <b>Введите новый день недели:</b>", parse_mode="HTML")
    await state.set_state(ScheduleStates.editing_field)
    await callback.answer()

@router.callback_query(F.data.startswith("edit_lesson_time_"))
async def edit_lesson_time_handler(callback: CallbackQuery, state: FSMContext):
    """Редактирование времени"""
    lesson_id = int(callback.data.split("_")[3])
    await state.update_data(edit_lesson_id=lesson_id, edit_field="time")
    await callback.message.answer("⏰ <b>Введите новое время (начало-конец, например: 10:00-11:30):</b>", parse_mode="HTML")
    await state.set_state(ScheduleStates.editing_field)
    await callback.answer()

@router.callback_query(F.data.startswith("edit_lesson_room_"))
async def edit_lesson_room_handler(callback: CallbackQuery, state: FSMContext):
    """Редактирование аудитории"""
    lesson_id = int(callback.data.split("_")[3])
    await state.update_data(edit_lesson_id=lesson_id, edit_field="room")
    await callback.message.answer("🏫 <b>Введите новый номер аудитории (или 'нет'):</b>", parse_mode="HTML")
    await state.set_state(ScheduleStates.editing_field)
    await callback.answer()

@router.callback_query(F.data.startswith("edit_lesson_teacher_"))
async def edit_lesson_teacher_handler(callback: CallbackQuery, state: FSMContext):
    """Редактирование преподавателя"""
    lesson_id = int(callback.data.split("_")[3])
    await state.update_data(edit_lesson_id=lesson_id, edit_field="teacher")
    await callback.message.answer("👨‍🏫 <b>Введите новое ФИО преподавателя (или 'нет'):</b>", parse_mode="HTML")
    await state.set_state(ScheduleStates.editing_field)
    await callback.answer()

@router.message(ScheduleStates.editing_field)
async def process_edit_field(message: Message, state: FSMContext):
    """Обработка редактирования поля"""
    data = await state.get_data()
    
    if 'edit_lesson_id' not in data or 'edit_field' not in data:
        await message.answer("❌ <b>Ошибка редактирования.</b> Попробуйте снова.", parse_mode="HTML")
        await state.clear()
        return
    
    lesson_id = data['edit_lesson_id']
    field = data['edit_field']
    new_value = message.text.strip()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT subject, day_of_week FROM schedule WHERE id = ?', (lesson_id,))
    lesson_info = cursor.fetchone()
    
    if not lesson_info:
        await message.answer("❌ <b>Урок не найден!</b>", parse_mode="HTML")
        await state.clear()
        conn.close()
        return
    
    field_updated = False
    field_name = ""
    
    if field == "subject":
        cursor.execute('UPDATE schedule SET subject = ? WHERE id = ?', (new_value, lesson_id))
        field_name = "предмет"
        field_updated = True
    elif field == "day":
        cursor.execute('UPDATE schedule SET day_of_week = ? WHERE id = ?', (new_value, lesson_id))
        field_name = "день недели"
        field_updated = True
    elif field == "time":
        if '-' in new_value:
            try:
                start_time, end_time = new_value.split('-')
                start_time = start_time.strip()
                end_time = end_time.strip()
                if ':' in start_time and ':' in end_time:
                    cursor.execute('UPDATE schedule SET start_time = ?, end_time = ? WHERE id = ?', 
                                  (start_time, end_time, lesson_id))
                    field_name = "время"
                    field_updated = True
                else:
                    await message.answer("❌ <b>Неверный формат времени!</b> Используйте ЧЧ:ММ-ЧЧ:ММ", parse_mode="HTML")
            except:
                await message.answer("❌ <b>Неверный формат времени!</b> Используйте начало-конец (например: 10:00-11:30)", parse_mode="HTML")
        else:
            await message.answer("❌ <b>Неверный формат времени!</b> Используйте начало-конец (например: 10:00-11:30)", parse_mode="HTML")
    elif field == "room":
        if new_value.lower() == 'нет':
            new_value = None
        cursor.execute('UPDATE schedule SET room = ? WHERE id = ?', (new_value, lesson_id))
        field_name = "аудитория"
        field_updated = True
    elif field == "teacher":
        if new_value.lower() == 'нет':
            new_value = None
        cursor.execute('UPDATE schedule SET teacher = ? WHERE id = ?', (new_value, lesson_id))
        field_name = "преподаватель"
        field_updated = True
    
    if field_updated:
        conn.commit()
        subject, day = lesson_info
        
        await message.answer(
            f"✅ <b>{field_name.capitalize()} успешно обновлен!</b>\n\n"
            f"Урок '{subject}' ({day}) изменен.",
            parse_mode="HTML"
        )
        
        # Показываем обновленный урок
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT subject, day_of_week, start_time, end_time, room, teacher 
            FROM schedule WHERE id = ?
        ''', (lesson_id,))
        
        lesson = cursor.fetchone()
        conn.close()
        
        if lesson:
            subject, day, start_time, end_time, room, teacher = lesson
            keyboard = get_lesson_detail_actions_keyboard(lesson_id)
            
            await message.answer(
                f"📋 <b>Обновленные детали урока:</b>\n\n"
                f"• <b>День:</b> {day}\n"
                f"• <b>Время:</b> {start_time}-{end_time}\n"
                f"• <b>Предмет:</b> {subject}\n"
                f"• <b>Аудитория:</b> {room or 'не указана'}\n"
                f"• <b>Преподаватель:</b> {teacher or 'не указан'}",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    else:
        await message.answer("❌ <b>Не удалось обновить поле.</b> Попробуйте еще раз.", parse_mode="HTML")
    
    conn.close()
    await state.clear()

# ==================== ОБРАБОТЧИКИ СОСТОЯНИЙ ДЛЯ ДОБАВЛЕНИЯ ====================

@router.message(ScheduleStates.waiting_for_subject)
async def process_subject(message: Message, state: FSMContext):
    """Обработка предмета"""
    await state.update_data(subject=message.text)
    await message.answer("⏰ <b>Введите время урока (например: 10:00-11:30):</b>", parse_mode="HTML")
    await state.set_state(ScheduleStates.waiting_for_time)

@router.message(ScheduleStates.waiting_for_time)
async def process_time(message: Message, state: FSMContext):
    """Обработка времени"""
    time_input = message.text.strip()
    
    if '-' not in time_input:
        await message.answer("❌ <b>Неверный формат!</b> Используйте: начало-конец (например: 10:00-11:30)", parse_mode="HTML")
        return
    
    start_time, end_time = time_input.split('-')
    await state.update_data(start_time=start_time.strip(), end_time=end_time.strip())
    await message.answer("🏫 <b>Введите номер аудитории (или 'нет'):</b>", parse_mode="HTML")
    await state.set_state(ScheduleStates.waiting_for_room)

@router.message(ScheduleStates.waiting_for_room)
async def process_room(message: Message, state: FSMContext):
    """Обработка аудитории"""
    room = message.text.strip()
    if room.lower() == 'нет' or room == '':
        room = None
    
    await state.update_data(room=room)
    await message.answer("👨‍🏫 <b>Введите ФИО преподавателя (или 'нет'):</b>", parse_mode="HTML")
    await state.set_state(ScheduleStates.waiting_for_teacher)

@router.message(ScheduleStates.waiting_for_teacher)
async def process_teacher(message: Message, state: FSMContext):
    """Обработка преподавателя и сохранение урока"""
    teacher = message.text.strip()
    if teacher.lower() == 'нет' or teacher == '':
        teacher = None
    
    data = await state.get_data()
    user_id = message.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO schedule (user_id, subject, day_of_week, start_time, end_time, room, teacher)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, data['subject'], data['day'], 
          data['start_time'], data['end_time'], data['room'], teacher))
    conn.commit()
    conn.close()
    
    await message.answer(
        f"✅ <b>Урок добавлен в расписание!</b>\n\n"
        f"📅 День: {data['day']}\n"
        f"📚 Предмет: {data['subject']}\n"
        f"⏰ Время: {data['start_time']}-{data['end_time']}\n"
        f"🏫 Аудитория: {data['room'] or 'не указана'}\n"
        f"👨‍🏫 Преподаватель: {teacher or 'не указан'}",
        parse_mode="HTML"
    )
    
    await state.clear()
    await show_interactive_schedule(message)

# ==================== КОМАНДЫ ====================

@router.message(Command("schedule"))
async def cmd_schedule(message: Message):
    """Команда /schedule"""
    await show_interactive_schedule(message)

@router.message(Command("add_lesson"))
async def quick_add_lesson(message: Message):
    """Быстрое добавление урока через команду"""
    await message.answer(
        "📝 <b>Быстрое добавление урока:</b>\n\n"
        "Используйте формат:\n"
        "<code>/add день предмет время аудитория преподаватель</code>\n\n"
        "Пример:\n"
        "<code>/add Понедельник Математика 10:00-11:30 101 Иванов И.И.</code>\n\n"
        "<i>Или используйте кнопки для пошагового добавления.</i>",
        parse_mode="HTML"
    )

@router.message(Command("add"))
async def add_lesson_quick(message: Message):
    """Быстрое добавление одной командой"""
    try:
        parts = message.text.split(maxsplit=5)
        if len(parts) < 5:
            await message.answer("❌ <b>Недостаточно параметров!</b>", parse_mode="HTML")
            return
        
        _, day, subject, time_range, room, teacher = parts
        
        if '-' in time_range:
            start_time, end_time = time_range.split('-')
        else:
            start_time = time_range
            end_time = "11:30"
        
        user_id = message.from_user.id
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO schedule (user_id, subject, day_of_week, start_time, end_time, room, teacher)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, subject, day, start_time, end_time, room, teacher))
        conn.commit()
        conn.close()
        
        await message.answer(
            f"✅ <b>Урок добавлен!</b>\n\n"
            f"📅 {day}\n"
            f"📚 {subject}\n"
            f"⏰ {start_time}-{end_time}\n"
            f"🏫 Ауд. {room}\n"
            f"👨‍🏫 {teacher}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        await message.answer(f"❌ <b>Ошибка:</b> {str(e)}", parse_mode="HTML")