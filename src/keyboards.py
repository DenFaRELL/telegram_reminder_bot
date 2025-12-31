# src/keyboards.py
from datetime import datetime

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
        [KeyboardButton(text="❓ Помощь")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True,
        one_time_keyboard=False,
        is_persistent=True,
    )


# ==================== INLINE КЛАВИАТУРЫ РАСПИСАНИЯ ====================


def get_schedule_list_keyboard():
    """Кнопки для списка расписания"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="➕ Добавить урок", callback_data="add_lesson_btn"
            ),
            InlineKeyboardButton(text="❓ Помощь", callback_data="schedule_help_btn"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_add_lesson_keyboard():
    """Inline-кнопки для выбора дня недели"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="Понедельник", callback_data="add_lesson_day_Понедельник"
            ),
            InlineKeyboardButton(
                text="Вторник", callback_data="add_lesson_day_Вторник"
            ),
        ],
        [
            InlineKeyboardButton(text="Среда", callback_data="add_lesson_day_Среда"),
            InlineKeyboardButton(
                text="Четверг", callback_data="add_lesson_day_Четверг"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Пятница", callback_data="add_lesson_day_Пятница"
            ),
            InlineKeyboardButton(
                text="Суббота", callback_data="add_lesson_day_Суббота"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_lessons_selection_keyboard(lessons, start_index=0):
    """Клавиатура для выбора урока из списка"""
    keyboard = []

    for i, lesson in enumerate(lessons[start_index : start_index + 5], start=1):
        lesson_id = lesson["id"]
        subject = lesson["subject"][:20]
        day = lesson["day_of_week"]
        time = lesson["start_time"]
        button_text = f"{start_index + i}. {day[:3]} {time} - {subject}"

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=button_text, callback_data=f"view_lesson_{lesson_id}"
                )
            ]
        )

    # Кнопки навигации если много уроков
    nav_buttons = []
    if start_index > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"lessons_page_{max(0, start_index - 5)}"
            )
        )

    if len(lessons) > start_index + 5:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Далее ➡️", callback_data=f"lessons_page_{start_index + 5}"
            )
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Кнопки добавления и помощи
    keyboard.append(
        [
            InlineKeyboardButton(
                text="➕ Добавить урок", callback_data="add_lesson_btn"
            ),
            InlineKeyboardButton(text="❓ Помощь", callback_data="schedule_help_btn"),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_lesson_detail_keyboard(lesson_id):
    """Кнопки для деталей урока"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✏️ Редактировать", callback_data=f"lesson_edit_{lesson_id}"
            ),
            InlineKeyboardButton(
                text="🗑️ Удалить", callback_data=f"lesson_delete_{lesson_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к расписанию", callback_data="back_to_schedule"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_edit_lesson_keyboard(lesson_id):
    """Клавиатура для редактирования урока"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="📚 Название", callback_data=f"edit_field_subject_{lesson_id}"
            ),
            InlineKeyboardButton(
                text="📅 День", callback_data=f"edit_field_day_{lesson_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🕒 Время", callback_data=f"edit_field_time_{lesson_id}"
            ),
            InlineKeyboardButton(
                text="🏢 Корпус", callback_data=f"edit_field_build_{lesson_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🚪 Аудитория", callback_data=f"edit_field_room_{lesson_id}"
            ),
            InlineKeyboardButton(
                text="👨‍🏫 Преподаватель",
                callback_data=f"edit_field_teacher_{lesson_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к уроку", callback_data=f"back_to_lesson_{lesson_id}"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_delete_confirmation_keyboard(lesson_id):
    """Клавиатура подтверждения удаления урока"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Да, удалить",
                callback_data=f"lesson_confirm_delete_{lesson_id}",
            ),
            InlineKeyboardButton(
                text="❌ Нет, вернуться", callback_data=f"back_to_lesson_{lesson_id}"
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_day_selection_keyboard(for_edit=False, lesson_id=None):
    """Inline-кнопки для выбора дня недели (для редактирования)"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="Понедельник",
                callback_data=(
                    f"select_day_Понедельник_{lesson_id}"
                    if for_edit
                    else "add_lesson_day_Понедельник"
                ),
            ),
            InlineKeyboardButton(
                text="Вторник",
                callback_data=(
                    f"select_day_Вторник_{lesson_id}"
                    if for_edit
                    else "add_lesson_day_Вторник"
                ),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Среда",
                callback_data=(
                    f"select_day_Среда_{lesson_id}"
                    if for_edit
                    else "add_lesson_day_Среда"
                ),
            ),
            InlineKeyboardButton(
                text="Четверг",
                callback_data=(
                    f"select_day_Четверг_{lesson_id}"
                    if for_edit
                    else "add_lesson_day_Четверг"
                ),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Пятница",
                callback_data=(
                    f"select_day_Пятница_{lesson_id}"
                    if for_edit
                    else "add_lesson_day_Пятница"
                ),
            ),
            InlineKeyboardButton(
                text="Суббота",
                callback_data=(
                    f"select_day_Суббота_{lesson_id}"
                    if for_edit
                    else "add_lesson_day_Суббота"
                ),
            ),
        ],
    ]
    if for_edit:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 Назад к уроку", callback_data=f"back_to_lesson_{lesson_id}"
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ==================== INLINE КЛАВИАТУРЫ ЗАДАЧ ====================


def get_tasks_list_keyboard():
    """Кнопки для списка задач"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="➕ Добавить задачу", callback_data="add_task_btn"
            ),
            InlineKeyboardButton(text="❓ Помощь", callback_data="tasks_help_btn"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_tasks_selection_keyboard(tasks, start_index=0):
    """Клавиатура для выбора задачи из списка"""
    keyboard = []

    for i, task in enumerate(tasks[start_index : start_index + 5], start=1):
        task_id = task["id"]
        title = task["title"][:25]
        button_text = f"{start_index + i}. {title}"

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=button_text, callback_data=f"view_task_{task_id}"
                )
            ]
        )

    # Кнопки навигации если много задач
    nav_buttons = []
    if start_index > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"tasks_page_{max(0, start_index - 5)}"
            )
        )

    if len(tasks) > start_index + 5:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Далее ➡️", callback_data=f"tasks_page_{start_index + 5}"
            )
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Кнопки добавления и помощи
    keyboard.append(
        [
            InlineKeyboardButton(
                text="➕ Добавить задачу", callback_data="add_task_btn"
            ),
            InlineKeyboardButton(text="❓ Помощь", callback_data="tasks_help_btn"),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_task_detail_keyboard(task_id):
    """Кнопки для деталей задачи"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Завершить", callback_data=f"complete_task_{task_id}"
            ),
            InlineKeyboardButton(
                text="✏️ Редактировать", callback_data=f"edit_task_{task_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Удалить", callback_data=f"delete_task_{task_id}"
            ),
            InlineKeyboardButton(
                text="🔙 Назад к задачам", callback_data="back_to_tasks"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_edit_task_keyboard(task_id):
    """Клавиатура для редактирования задачи"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="📝 Название", callback_data=f"edit_task_field_title_{task_id}"
            ),
            InlineKeyboardButton(
                text="📄 Описание",
                callback_data=f"edit_task_field_description_{task_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📅 Дедлайн", callback_data=f"edit_task_field_deadline_{task_id}"
            ),
            InlineKeyboardButton(
                text="🎯 Приоритет", callback_data=f"edit_task_field_priority_{task_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к задаче", callback_data=f"back_to_task_{task_id}"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_priority_selection_keyboard(for_edit=False, task_id=None):
    """Клавиатура для выбора приоритета"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔴 Высокий",
                callback_data=(
                    f"select_priority_high_{task_id}"
                    if for_edit and task_id
                    else "select_priority_high"
                ),
            ),
            InlineKeyboardButton(
                text="🟡 Средний",
                callback_data=(
                    f"select_priority_medium_{task_id}"
                    if for_edit and task_id
                    else "select_priority_medium"
                ),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🟢 Низкий",
                callback_data=(
                    f"select_priority_low_{task_id}"
                    if for_edit and task_id
                    else "select_priority_low"
                ),
            )
        ],
    ]
    if for_edit and task_id:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 Назад к задаче", callback_data=f"back_to_task_{task_id}"
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_delete_task_confirmation_keyboard(task_id):
    """Клавиатура подтверждения удаления задачи"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Да, удалить", callback_data=f"confirm_delete_task_{task_id}"
            ),
            InlineKeyboardButton(
                text="❌ Нет, вернуться", callback_data=f"back_to_task_{task_id}"
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ==================== INLINE КЛАВИАТУРЫ СОБЫТИЙ ====================


def get_events_list_keyboard():
    """Кнопки для списка событий"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="➕ Добавить событие", callback_data="add_event_btn"
            ),
            InlineKeyboardButton(text="❓ Помощь", callback_data="events_help_btn"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_events_selection_keyboard(events, start_index=0):
    """Клавиатура для выбора события из списка"""
    keyboard = []

    for i, event in enumerate(events[start_index : start_index + 5], start=1):
        event_id = event["id"]
        title = event["title"][:25]

        # Форматируем дату из ГГГГ-ММ-ДД ЧЧ:ММ в ДД.ММ.ГГГГ
        event_date_time = event["event_datetime"]
        try:
            dt = datetime.strptime(event_date_time, "%Y-%m-%d %H:%M")
            formatted_date = dt.strftime("%d.%m.%Y")
        except Exception:
            formatted_date = event_date_time[:10]

        button_text = f"{start_index + i}. {formatted_date} - {title}"

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=button_text, callback_data=f"view_event_{event_id}"
                )
            ]
        )

    # Кнопки навигации если много событий
    nav_buttons = []
    if start_index > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"events_page_{max(0, start_index - 5)}"
            )
        )

    if len(events) > start_index + 5:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Далее ➡️", callback_data=f"events_page_{start_index + 5}"
            )
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Кнопки добавления и помощи
    keyboard.append(
        [
            InlineKeyboardButton(
                text="➕ Добавить событие", callback_data="add_event_btn"
            ),
            InlineKeyboardButton(text="❓ Помощь", callback_data="events_help_btn"),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_event_detail_keyboard(event_id):
    """Кнопки для деталей события"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✏️ Редактировать", callback_data=f"edit_event_{event_id}"
            ),
            InlineKeyboardButton(
                text="🗑️ Удалить", callback_data=f"delete_event_{event_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к событиям", callback_data="back_to_events"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_recurrence_keyboard(for_edit=False, event_id=None):
    """Клавиатура для выбора повторяемости события"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="❌ Не повторяется",
                callback_data=(
                    f"select_recurrence_none_{event_id}"
                    if for_edit
                    else "select_recurrence_none"
                ),
            ),
            InlineKeyboardButton(
                text="📅 Ежедневно",
                callback_data=(
                    f"select_recurrence_daily_{event_id}"
                    if for_edit
                    else "select_recurrence_daily"
                ),
            ),
        ],
        [
            InlineKeyboardButton(
                text="📅 Еженедельно",
                callback_data=(
                    f"select_recurrence_weekly_{event_id}"
                    if for_edit
                    else "select_recurrence_weekly"
                ),
            ),
            InlineKeyboardButton(
                text="📅 Ежемесячно",
                callback_data=(
                    f"select_recurrence_monthly_{event_id}"
                    if for_edit
                    else "select_recurrence_monthly"
                ),
            ),
        ],
        [
            InlineKeyboardButton(
                text="📅 Ежегодно",
                callback_data=(
                    f"select_recurrence_yearly_{event_id}"
                    if for_edit
                    else "select_recurrence_yearly"
                ),
            )
        ],
    ]
    if for_edit:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 Назад к событию", callback_data=f"back_to_event_{event_id}"
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_weekday_selection_keyboard(for_edit=False, event_id=None):
    """Клавиатура для выбора дней недели (для еженедельных событий)"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="Пн",
                callback_data=(
                    f"select_weekday_1_{event_id}" if for_edit else "select_weekday_1"
                ),
            ),
            InlineKeyboardButton(
                text="Вт",
                callback_data=(
                    f"select_weekday_2_{event_id}" if for_edit else "select_weekday_2"
                ),
            ),
            InlineKeyboardButton(
                text="Ср",
                callback_data=(
                    f"select_weekday_3_{event_id}" if for_edit else "select_weekday_3"
                ),
            ),
            InlineKeyboardButton(
                text="Чт",
                callback_data=(
                    f"select_weekday_4_{event_id}" if for_edit else "select_weekday_4"
                ),
            ),
            InlineKeyboardButton(
                text="Пт",
                callback_data=(
                    f"select_weekday_5_{event_id}" if for_edit else "select_weekday_5"
                ),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Сб",
                callback_data=(
                    f"select_weekday_6_{event_id}" if for_edit else "select_weekday_6"
                ),
            ),
            InlineKeyboardButton(
                text="Вс",
                callback_data=(
                    f"select_weekday_7_{event_id}" if for_edit else "select_weekday_7"
                ),
            ),
        ],
    ]
    if for_edit:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 Назад", callback_data=f"back_to_event_{event_id}"
                )
            ]
        )
    else:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="✅ Готово", callback_data="weekday_selection_done"
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_edit_event_keyboard(event_id):
    """Клавиатура для редактирования события"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="📝 Название", callback_data=f"edit_event_field_title_{event_id}"
            ),
            InlineKeyboardButton(
                text="📄 Описание",
                callback_data=f"edit_event_field_description_{event_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📅 Дата и время",
                callback_data=f"edit_event_field_datetime_{event_id}",
            ),
            InlineKeyboardButton(
                text="📍 Место", callback_data=f"edit_event_field_location_{event_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔄 Повторяемость",
                callback_data=f"edit_event_field_recurrence_{event_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к событию", callback_data=f"back_to_event_{event_id}"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_delete_event_confirmation_keyboard(event_id):
    """Клавиатура подтверждения удаления события"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Да, удалить", callback_data=f"confirm_delete_event_{event_id}"
            ),
            InlineKeyboardButton(
                text="❌ Нет, вернуться", callback_data=f"back_to_event_{event_id}"
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
