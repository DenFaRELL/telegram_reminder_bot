# src/states.py
"""Состояния для FSM"""

from aiogram.fsm.state import State, StatesGroup

# ==================== СОСТОЯНИЯ ДЛЯ РАСПИСАНИЯ ====================

class AddLessonStates(StatesGroup):
    """Состояния для добавления урока"""
    waiting_for_subject = State()
    waiting_for_time = State()
    waiting_for_build = State()
    waiting_for_room = State()
    waiting_for_teacher = State()


class EditLessonStates(StatesGroup):
    """Состояния для редактирования урока"""
    waiting_for_field_value = State()


# ==================== СОСТОЯНИЯ ДЛЯ ЗАДАЧ ====================

class AddTaskStates(StatesGroup):
    """Состояния для добавления задачи"""
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_deadline = State()
    waiting_for_priority = State()


class EditTaskStates(StatesGroup):
    """Состояния для редактирования задачи"""
    waiting_for_field_value = State()


# ==================== СОСТОЯНИЯ ДЛЯ СОБЫТИЙ ====================

class AddEventStates(StatesGroup):
    """Состояния для добавления события"""
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_datetime = State()
    waiting_for_location = State()
    waiting_for_recurrence = State()


class EditEventStates(StatesGroup):
    """Состояния для редактирования события"""
    waiting_for_field_value = State()
