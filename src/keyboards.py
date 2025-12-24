# src/keyboard.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==================== REPLY КЛАВИАТУРЫ (внизу экрана) ====================

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Основная клавиатура (главное меню)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Расписание"), KeyboardButton(text="✅ Задачи")],
            [KeyboardButton(text="➕ Добавить задачу"), KeyboardButton(text="🎯 События")],
            [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="📊 Статистика")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )

def get_schedule_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для управления расписанием"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить урок"), KeyboardButton(text="📋 Показать расписание")],
            [KeyboardButton(text="✏️ Редактировать урок"), KeyboardButton(text="🗑️ Удалить урок")],
            [KeyboardButton(text="🔙 Назад в меню"), KeyboardButton(text="❓ Помощь по расписанию")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Управление расписанием..."
    )

def get_add_lesson_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для добавления урока (выбор дня недели)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Понедельник"), KeyboardButton(text="📅 Вторник")],
            [KeyboardButton(text="📅 Среда"), KeyboardButton(text="📅 Четверг")],
            [KeyboardButton(text="📅 Пятница"), KeyboardButton(text="📅 Суббота")],
            [KeyboardButton(text="📅 Воскресенье"), KeyboardButton(text="🔙 Назад к расписанию")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите день недели..."
    )

def get_tasks_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для управления задачами"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Показать задачи"), KeyboardButton(text="➕ Новая задача")],
            [KeyboardButton(text="✅ Завершить задачу"), KeyboardButton(text="🔥 Срочные задачи")],
            [KeyboardButton(text="🔙 Назад в меню"), KeyboardButton(text="📊 Статистика задач")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Управление задачами..."
    )

def get_events_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для управления событиями"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Показать события"), KeyboardButton(text="➕ Новое событие")],
            [KeyboardButton(text="🗑️ Удалить событие"), KeyboardButton(text="🔔 Ближайшие события")],
            [KeyboardButton(text="🔙 Назад в меню"), KeyboardButton(text="❓ Помощь по событиям")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Управление событиями..."
    )

# ==================== INLINE КЛАВИАТУРЫ (в сообщениях) ====================

def get_schedule_actions_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавиатура для действий с расписанием"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить урок", callback_data="add_lesson"),
        InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_lesson_menu")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Удалить урок", callback_data="delete_lesson_menu"),
        InlineKeyboardButton(text="📋 Показать всё", callback_data="view_all_schedule")
    )
    return builder.as_markup()

def get_lesson_actions_keyboard(lesson_id: int) -> InlineKeyboardMarkup:
    """Inline-клавиатура для действий с конкретным уроком"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_lesson_{lesson_id}"),
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"view_lesson_{lesson_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_schedule")
    )
    return builder.as_markup()

def get_lesson_detail_actions_keyboard(lesson_id: int) -> InlineKeyboardMarkup:
    """Inline-клавиатура для детального просмотра урока"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_lesson_{lesson_id}"),
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"confirm_delete_{lesson_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_schedule")
    )
    return builder.as_markup()

def get_edit_lesson_keyboard(lesson_id: int) -> InlineKeyboardMarkup:
    """Inline-клавиатура для редактирования урока"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 День недели", callback_data=f"edit_lesson_day_{lesson_id}"),
        InlineKeyboardButton(text="📚 Предмет", callback_data=f"edit_lesson_subject_{lesson_id}")
    )
    builder.row(
        InlineKeyboardButton(text="⏰ Время", callback_data=f"edit_lesson_time_{lesson_id}"),
        InlineKeyboardButton(text="🏫 Аудитория", callback_data=f"edit_lesson_room_{lesson_id}")
    )
    builder.row(
        InlineKeyboardButton(text="👨‍🏫 Преподаватель", callback_data=f"edit_lesson_teacher_{lesson_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"view_lesson_{lesson_id}")
    )
    return builder.as_markup()

def get_confirmation_keyboard(lesson_id: int) -> InlineKeyboardMarkup:
    """Inline-клавиатура для подтверждения удаления"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_now_{lesson_id}"),
        InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"view_lesson_{lesson_id}")
    )
    return builder.as_markup()

def get_task_actions_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавиатура для действий с задачами"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Завершить задачу", callback_data="complete_task_menu"),
        InlineKeyboardButton(text="🗑️ Удалить задачу", callback_data="delete_task_menu")
    )
    return builder.as_markup()

def get_event_actions_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавиатура для действий с событиями"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑️ Удалить событие", callback_data="delete_event_menu"),
        InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_event_menu")
    )
    return builder.as_markup()

def get_edit_event_keyboard(event_id: int) -> InlineKeyboardMarkup:
    """Inline-клавиатура для редактирования события"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎯 Название", callback_data=f"edit_event_title_{event_id}"),
        InlineKeyboardButton(text="📅 Дата", callback_data=f"edit_event_date_{event_id}")
    )
    builder.row(
        InlineKeyboardButton(text="⏰ Время", callback_data=f"edit_event_time_{event_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_events")
    )
    return builder.as_markup()

# ==================== УТИЛИТЫ ДЛЯ СОЗДАНИЯ КЛАВИАТУР ====================

def create_inline_keyboard_from_list(items: list, callback_prefix: str, back_callback: str = None) -> InlineKeyboardMarkup:
    """
    Создает inline-клавиатуру из списка элементов
    
    Args:
        items: список кортежей (id, text)
        callback_prefix: префикс для callback_data
        back_callback: callback_data для кнопки "Назад"
    
    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    for item_id, text in items:
        # Укорачиваем текст если слишком длинный
        if len(text) > 40:
            text = text[:37] + "..."
        builder.row(InlineKeyboardButton(text=text, callback_data=f"{callback_prefix}_{item_id}"))
    
    if back_callback:
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=back_callback))
    
    return builder.as_markup()

def create_simple_keyboard(buttons: list, row_width: int = 2) -> InlineKeyboardMarkup:
    """
    Создает простую inline-клавиатуру из списка кнопок
    
    Args:
        buttons: список кортежей (text, callback_data)
        row_width: количество кнопок в строке
    
    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    for text, callback_data in buttons:
        builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))
    
    builder.adjust(row_width)
    return builder.as_markup()