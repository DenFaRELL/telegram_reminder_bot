# src/states.py
from aiogram.fsm.state import State, StatesGroup


# Состояния для добавления урока
class AddLessonStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_time = State()
    waiting_for_build = State()
    waiting_for_room = State()
    waiting_for_teacher = State()


# Состояния для редактирования урока
class EditLessonStates(StatesGroup):
    waiting_for_field_value = State()


# Состояния для задач
class TaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_deadline = State()
    waiting_for_priority = State()


# Состояния для редактирования задач
class EditTaskStates(StatesGroup):
    waiting_for_field_value = State()


# Состояния для событий
class EventStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_datetime = State()
    waiting_for_location = State()
    waiting_for_recurrence = State()


# Состояния для редактирования событий
class EditEventStates(StatesGroup):
    waiting_for_field_value = State()
