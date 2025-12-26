# src/keyboards.py
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# ==================== ГЛАВНАЯ КЛАВИАТУРА ====================

def get_main_keyboard():
    """Главное меню - 2 кнопки в ряду"""
    keyboard = [
        [KeyboardButton(text="📅 Расписание"), KeyboardButton(text="✅ Задачи")],
        [KeyboardButton(text="🎯 События"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True,
        one_time_keyboard=False,
    )


def get_back_help_keyboard():
    """Клавиатура для разделов (2 кнопки в ряду)"""
    keyboard = [
        [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True,
        one_time_keyboard=False,
    )


# ==================== INLINE КЛАВИАТУРЫ (для действий) ====================

def get_add_lesson_keyboard():
    """Inline-кнопки для выбора дня недели (без воскресенья)"""
    keyboard = [
        [
            InlineKeyboardButton(text="Понедельник", callback_data="add_lesson_day_Понедельник"),
            InlineKeyboardButton(text="Вторник", callback_data="add_lesson_day_Вторник")
        ],
        [
            InlineKeyboardButton(text="Среда", callback_data="add_lesson_day_Среда"),
            InlineKeyboardButton(text="Четверг", callback_data="add_lesson_day_Четверг")
        ],
        [
            InlineKeyboardButton(text="Пятница", callback_data="add_lesson_day_Пятница"),
            InlineKeyboardButton(text="Суббота", callback_data="add_lesson_day_Суббота")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_schedule_actions_keyboard():
    """Inline-кнопки для действий с расписанием"""
    keyboard = [
        [
            InlineKeyboardButton(text="➕ Добавить урок", callback_data="add_lesson_btn"),
            InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_lessons_btn")
        ],
        [
            InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete_lessons_btn")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_schedule_actions_empty_keyboard():
    """Inline-кнопки для пустого расписания"""
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить первый урок", callback_data="add_lesson_btn")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
