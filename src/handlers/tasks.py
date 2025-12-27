# src/handlers/tasks.py
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.database import get_connection
from src.keyboards import (
    get_delete_task_confirmation_keyboard,
    get_edit_task_keyboard,
    get_priority_selection_keyboard,
    get_task_detail_keyboard,
    get_tasks_list_keyboard,
    get_tasks_selection_keyboard,
)
from src.states import EditTaskStates, TaskStates

router = Router()

# Глобальная переменная для user_current_section
user_current_section = {}
# Словарь для хранения временного списка задач по user_id
user_tasks_cache = {}


async def show_tasks_list(message: Message, user_id):
    """Показать список задач с inline-кнопками"""
    conn = get_connection()
    cursor = conn.cursor()

    # Получаем активные задачи
    cursor.execute(
        """
        SELECT id, title, description, deadline, priority, is_completed
        FROM tasks
        WHERE user_id = ? AND is_completed = FALSE
        ORDER BY
            CASE priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            deadline
        """,
        (user_id,),
    )

    active_tasks = [dict(row) for row in cursor.fetchall()]

    # Получаем завершённые задачи
    cursor.execute(
        """
        SELECT id, title, description, deadline, priority, is_completed
        FROM tasks
        WHERE user_id = ? AND is_completed = TRUE
        ORDER BY deadline DESC
        LIMIT 10
        """,
        (user_id,),
    )

    completed_tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Сохраняем задачи в кэш
    user_tasks_cache[user_id] = active_tasks

    if not active_tasks and not completed_tasks:
        response = "✅ <b>У вас пока нет задач!</b>\n\n"
        response += "Добавьте первую задачу с помощью кнопки ниже:"

        await message.answer(
            response,
            reply_markup=get_tasks_list_keyboard(),
            parse_mode="HTML",
        )
    else:
        response = "✅ <b>Ваши задачи:</b>\n\n"
        response += "<i>Выберите активную задачу для просмотра деталей:</i>\n\n"

        if active_tasks:
            response += "📋 <b>Активные задачи:</b>\n\n"

            for i, task in enumerate(active_tasks[:5], 1):
                title = task["title"]
                response += f"<b>{i}.</b> {title}\n"

                if task["deadline"]:
                    response += f"📅 <i>До: {task['deadline']}</i>\n"

                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    task["priority"], "⚪"
                )

                response += f"{priority_emoji} <i>Приоритет: {task['priority']}</i>\n\n"

        if completed_tasks:
            response += "\n🏁 <b>Завершённые задачи:</b>\n\n"

            for task in completed_tasks[:3]:  # Показываем только 3 завершенные
                title = task["title"]
                response += f"✅ <b>{title}</b>\n"

                if task["deadline"]:
                    response += f"📅 <i>Было до: {task['deadline']}</i>\n\n"
                else:
                    response += "\n"

        await message.answer(
            response,
            reply_markup=get_tasks_selection_keyboard(active_tasks),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("tasks_page_"))
async def tasks_page_handler(callback: CallbackQuery):
    """Обработка переключения страниц задач"""
    start_index = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    tasks = user_tasks_cache.get(user_id, [])

    if not tasks:
        await callback.answer("❌ Список задач пуст!")
        return

    response = "✅ <b>Активные задачи:</b>\n\n"
    response += "<i>Выберите задачу для просмотра деталей:</i>\n\n"

    for i, task in enumerate(tasks[start_index : start_index + 5], 1):
        title = task["title"]
        response += f"<b>{start_index + i}.</b> {title}\n"

        if task["deadline"]:
            response += f"📅 <i>До: {task['deadline']}</i>\n"

        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
            task["priority"], "⚪"
        )

        response += f"{priority_emoji} <i>Приоритет: {task['priority']}</i>\n\n"

    await callback.message.edit_text(
        response,
        parse_mode="HTML",
    )
    await callback.message.edit_reply_markup(
        reply_markup=get_tasks_selection_keyboard(tasks, start_index)
    )
    await callback.answer()


@router.message(F.text.contains("задача") | F.text.contains("task"))
async def handle_task_link(message: Message):
    """Обработка ссылок на задачи"""
    # Если это команда /start с параметром task
    if message.text.startswith("/start"):
        parts = message.text.split()
        if len(parts) > 1 and parts[1].startswith("task_"):
            task_id = int(parts[1].split("_")[1])
            await show_task_details(message, task_id)


async def show_task_details(message_or_callback, task_id):
    """Показать детали задачи"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = dict(cursor.fetchone())
    conn.close()

    if not task:
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer("❌ Задача не найдена!")
        else:
            await message_or_callback.answer("❌ Задача не найдена!")
        return

    # Формируем детальное описание задачи
    response = "✅ <b>Детали задачи:</b>\n\n"
    response += f"📝 <b>Название:</b> {task['title']}\n"

    if task["description"]:
        response += f"📄 <b>Описание:</b> {task['description']}\n"

    if task["deadline"]:
        # Проверяем, не просрочена ли задача
        deadline_date = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
        today = datetime.now().date()

        if deadline_date < today:
            response += f"⏰ <b>Дедлайн:</b> {task['deadline']} <b>(ПРОСРОЧЕНО!)</b>\n"
        else:
            days_left = (deadline_date - today).days
            response += (
                f"📅 <b>Дедлайн:</b> {task['deadline']} (осталось {days_left} дней)\n"
            )

    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
        task["priority"], "⚪"
    )

    response += f"🎯 <b>Приоритет:</b> {priority_emoji} {task['priority']}\n"
    response += f"📊 <b>Статус:</b> {'✅ Выполнена' if task['is_completed'] else '⏳ В работе'}\n"

    # Определяем куда отправлять ответ
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.answer(
            response, reply_markup=get_task_detail_keyboard(task_id), parse_mode="HTML"
        )
        await message_or_callback.answer()
    else:
        await message_or_callback.answer(
            response, reply_markup=get_task_detail_keyboard(task_id), parse_mode="HTML"
        )


@router.callback_query(F.data == "tasks_help_btn")
async def tasks_help_handler(callback: CallbackQuery):
    """Помощь по задачам"""
    from src.handlers.main import show_tasks_help

    await callback.answer()
    await show_tasks_help(callback.message)


@router.callback_query(F.data == "add_task_btn")
async def add_task_handler_callback(callback: CallbackQuery, state: FSMContext):
    """Начать добавление задачи через кнопку"""
    await callback.answer()
    user_id = callback.from_user.id
    user_current_section[user_id] = "tasks"

    await callback.message.answer(
        "📝 <b>Добавление новой задачи</b>\n\nВведите название задачи:",
        parse_mode="HTML",
    )

    await state.set_state(TaskStates.waiting_for_title)


@router.message(Command("add_task"))
async def add_task_handler_message(message: Message, state: FSMContext):
    """Начать добавление задачи через команду"""
    user_id = message.from_user.id
    user_current_section[user_id] = "tasks"

    await message.answer(
        "📝 <b>Добавление новой задачи</b>\n\nВведите название задачи:",
        parse_mode="HTML",
    )

    await state.set_state(TaskStates.waiting_for_title)


@router.message(TaskStates.waiting_for_title)
async def process_task_title(message: Message, state: FSMContext):
    """Обработка названия задачи"""
    await state.update_data(title=message.text)

    await message.answer(
        "📝 <b>Введите описание задачи (или напишите 'нет' если не нужно):</b>",
        parse_mode="HTML",
    )

    await state.set_state(TaskStates.waiting_for_description)


@router.message(TaskStates.waiting_for_description)
async def process_task_description(message: Message, state: FSMContext):
    """Обработка описания задачи"""
    description = message.text.strip()
    if description.lower() == "нет" or not description:
        description = None

    await state.update_data(description=description)

    await message.answer(
        "📅 <b>Введите дедлайн задачи (формат: ГГГГ-ММ-ДД, или напишите 'нет'):</b>\n"
        "<i>Пример: 2024-12-31</i>",
        parse_mode="HTML",
    )

    await state.set_state(TaskStates.waiting_for_deadline)


@router.message(TaskStates.waiting_for_deadline)
async def process_task_deadline(message: Message, state: FSMContext):
    """Обработка дедлайна задачи"""
    deadline = message.text.strip()

    if deadline.lower() == "нет" or not deadline:
        deadline = None
    else:
        # Проверяем формат даты
        try:
            datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            await message.answer(
                "❌ <b>Неверный формат даты!</b>\n"
                "Используйте формат: ГГГГ-ММ-ДД\n"
                "Пример: 2024-12-31",
                parse_mode="HTML",
            )
            return

    await state.update_data(deadline=deadline)

    await message.answer(
        "🎯 <b>Выберите приоритет задачи:</b>",
        reply_markup=get_priority_selection_keyboard(),
        parse_mode="HTML",
    )

    await state.set_state(TaskStates.waiting_for_priority)


@router.callback_query(F.data.startswith("select_priority_"))
async def process_task_priority(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора приоритета задачи"""
    priority = callback.data.split("_")[2]  # high, medium, low

    # Получаем все данные из состояния
    data = await state.get_data()
    user_id = callback.from_user.id

    # Сохраняем задачу в базу данных
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO tasks (user_id, title, description, deadline, priority, is_completed)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                data["title"],
                data.get("description"),
                data.get("deadline"),
                priority,
                False,  # is_completed
            ),
        )
        conn.commit()

        response = "✅ <b>Задача успешно добавлена!</b>\n\n"
        response += f"<b>Название:</b> {data['title']}\n"

        if data.get("description"):
            response += f"<b>Описание:</b> {data['description']}\n"

        if data.get("deadline"):
            response += f"<b>Дедлайн:</b> {data['deadline']}\n"

        priority_emoji = {
            "high": "🔴 Высокий",
            "medium": "🟡 Средний",
            "low": "🟢 Низкий",
        }
        response += f"<b>Приоритет:</b> {priority_emoji[priority]}\n"

        await callback.message.answer(response, parse_mode="HTML")

        # Показываем кнопку для возврата к списку задач
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Вернуться к задачам", callback_data="back_to_tasks"
                    )
                ]
            ]
        )

        await callback.message.answer(
            "<b>Нажмите кнопку чтобы вернуться к задачам:</b>",
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    except Exception as e:
        await callback.message.answer(
            f"❌ <b>Ошибка при сохранении задачи:</b>\n{str(e)}", parse_mode="HTML"
        )

    finally:
        conn.close()
        await state.clear()
        await callback.answer()


# ==================== ОБРАБОТКА ДЕТАЛЕЙ, РЕДАКТИРОВАНИЯ И УДАЛЕНИЯ ЗАДАЧ ====================


@router.callback_query(F.data.startswith("view_task_"))
async def view_task_handler(callback: CallbackQuery):
    """Показать детали задачи"""
    task_id = int(callback.data.split("_")[2])
    await show_task_details(callback, task_id)


@router.callback_query(F.data.startswith("complete_task_"))
async def complete_task_handler(callback: CallbackQuery):
    """Завершить задачу"""
    task_id = int(callback.data.split("_")[2])

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET is_completed = TRUE WHERE id = ?", (task_id,))
    conn.commit()

    cursor.execute("SELECT title FROM tasks WHERE id = ?", (task_id,))
    task_title = cursor.fetchone()["title"]
    conn.close()

    await callback.answer(f"✅ Задача '{task_title}' завершена!")

    await callback.message.edit_text(
        f"✅ <b>Задача '{task_title}' успешно завершена!</b>\n\n"
        f"Нажмите кнопку чтобы вернуться к задачам:",
        parse_mode="HTML",
    )

    # Кнопка для возврата к задачам
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Вернуться к задачам", callback_data="back_to_tasks"
                )
            ]
        ]
    )
    await callback.message.edit_reply_markup(reply_markup=keyboard)


@router.callback_query(F.data.startswith("edit_task_"))
async def edit_task_selected(callback: CallbackQuery):
    """Выбрана задача для редактирования"""
    task_id = int(callback.data.split("_")[2])
    await callback.answer()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = dict(cursor.fetchone())
    conn.close()

    if not task:
        await callback.message.answer("❌ Задача не найдена!")
        return

    # Показываем информацию о задаче и кнопки редактирования
    response = f"✏️ <b>Редактирование задачи:</b>\n\n"
    response += f"📝 <b>Название:</b> {task['title']}\n"

    if task["description"]:
        response += f"📄 <b>Описание:</b> {task['description']}\n"

    if task["deadline"]:
        response += f"📅 <b>Дедлайн:</b> {task['deadline']}\n"

    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
        task["priority"], "⚪"
    )

    response += f"🎯 <b>Приоритет:</b> {priority_emoji} {task['priority']}\n"
    response += f"📊 <b>Статус:</b> {'✅ Выполнена' if task['is_completed'] else '⏳ В работе'}\n"

    response += "\n<b>Выберите что изменить:</b>"

    await callback.message.edit_text(response, parse_mode="HTML")
    await callback.message.edit_reply_markup(
        reply_markup=get_edit_task_keyboard(task_id)
    )


@router.callback_query(F.data.startswith("delete_task_"))
async def delete_task_selected(callback: CallbackQuery):
    """Выбрана задача для удаления"""
    task_id = int(callback.data.split("_")[2])
    await callback.answer()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = dict(cursor.fetchone())
    conn.close()

    if not task:
        await callback.message.answer("❌ Задача не найдена!")
        return

    # Показываем информацию о задаче и кнопку подтверждения
    response = f"🗑️ <b>Удаление задачи:</b>\n\n"
    response += f"📝 <b>Название:</b> {task['title']}\n"

    if task["description"]:
        response += f"📄 <b>Описание:</b> {task['description']}\n"

    if task["deadline"]:
        response += f"📅 <b>Дедлайн:</b> {task['deadline']}\n"

    response += f"📊 <b>Статус:</b> {'✅ Выполнена' if task['is_completed'] else '⏳ В работе'}\n"

    response += "\n<b>Вы действительно хотите удалить эту задачу?</b>"

    await callback.message.edit_text(response, parse_mode="HTML")
    await callback.message.edit_reply_markup(
        reply_markup=get_delete_task_confirmation_keyboard(task_id)
    )


@router.callback_query(F.data.startswith("confirm_delete_task_"))
async def confirm_delete_task(callback: CallbackQuery):
    """Подтверждение удаления задачи"""
    task_id = int(callback.data.split("_")[3])

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    await callback.answer("✅ Задача удалена!")
    await callback.message.edit_text(
        "✅ <b>Задача успешно удалена!</b>\n\nНажмите кнопку чтобы вернуться к задачам:",
        parse_mode="HTML",
    )

    # Кнопка для возврата к задачам
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Вернуться к задачам", callback_data="back_to_tasks"
                )
            ]
        ]
    )
    await callback.message.edit_reply_markup(reply_markup=keyboard)


@router.callback_query(F.data.startswith("edit_task_field_"))
async def edit_task_field_selected(callback: CallbackQuery, state: FSMContext):
    """Выбрано поле задачи для редактирования"""
    data_parts = callback.data.split("_")
    field_name = data_parts[3]
    task_id = int(data_parts[4])

    await callback.answer()

    # Сохраняем информацию в состоянии
    await state.update_data(task_id=task_id, field_name=field_name)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = dict(cursor.fetchone())
    conn.close()

    if field_name == "priority":
        await callback.message.edit_text(
            "🎯 <b>Выберите новый приоритет задачи:</b>", parse_mode="HTML"
        )
        await callback.message.edit_reply_markup(
            reply_markup=get_priority_selection_keyboard(for_edit=True, task_id=task_id)
        )
    else:
        field_names = {
            "title": "название задачи",
            "description": "описание задачи (или 'нет' если не нужно)",
            "deadline": "дедлайн задачи (формат: ГГГГ-ММ-ДД, или 'нет')",
        }

        current_value = task.get(field_name, "")

        await callback.message.edit_text(
            f"✏️ <b>Редактирование {field_names[field_name]}</b>\n\n"
            f"Текущее значение: <code>{current_value if current_value else 'не указано'}</code>\n\n"
            f"<b>Введите новое значение:</b>",
            parse_mode="HTML",
        )
        await callback.message.edit_reply_markup(reply_markup=None)

        await state.set_state(EditTaskStates.waiting_for_field_value)


@router.message(EditTaskStates.waiting_for_field_value)
async def process_task_field_value(message: Message, state: FSMContext):
    """Обработка нового значения поля задачи"""
    data = await state.get_data()
    task_id = data["task_id"]
    field_name = data["field_name"]
    new_value = message.text.strip()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        if field_name == "deadline":
            if new_value.lower() == "нет" or not new_value:
                new_value = None
            else:
                # Проверяем формат даты
                try:
                    datetime.strptime(new_value, "%Y-%m-%d")
                except ValueError:
                    await message.answer(
                        "❌ <b>Неверный формат даты!</b>\n"
                        "Используйте формат: ГГГГ-ММ-ДД\n"
                        "Пример: 2024-12-31",
                        parse_mode="HTML",
                    )
                    return
        else:
            if new_value.lower() == "нет" or not new_value:
                new_value = None

        if field_name == "title":
            cursor.execute(
                "UPDATE tasks SET title = ? WHERE id = ?", (new_value, task_id)
            )
        elif field_name == "description":
            cursor.execute(
                "UPDATE tasks SET description = ? WHERE id = ?", (new_value, task_id)
            )
        elif field_name == "deadline":
            cursor.execute(
                "UPDATE tasks SET deadline = ? WHERE id = ?", (new_value, task_id)
            )

        conn.commit()

        field_display_names = {
            "title": "Название задачи",
            "description": "Описание задачи",
            "deadline": "Дедлайн задачи",
        }

        await message.answer(
            f"✅ <b>{field_display_names[field_name]} успешно обновлено!</b>",
            parse_mode="HTML",
        )

        # После обновления возвращаемся к деталям задачи
        await show_task_details(message, task_id)

    except Exception as e:
        await message.answer(
            f"❌ <b>Ошибка при обновлении:</b>\n{str(e)}", parse_mode="HTML"
        )
    finally:
        conn.close()
        await state.clear()


@router.callback_query(F.data.startswith("back_to_task_"))
async def back_to_task(callback: CallbackQuery):
    """Вернуться к деталям задачи"""
    task_id = int(callback.data.split("_")[3])
    await show_task_details(callback, task_id)


@router.callback_query(F.data == "back_to_tasks")
async def back_to_tasks_handler(callback: CallbackQuery):
    """Вернуться к списку задач"""
    await callback.answer()

    user_id = callback.from_user.id
    user_current_section[user_id] = "tasks"

    conn = get_connection()
    cursor = conn.cursor()

    # Получаем активные задачи
    cursor.execute(
        """
        SELECT id, title, description, deadline, priority, is_completed
        FROM tasks
        WHERE user_id = ? AND is_completed = FALSE
        ORDER BY
            CASE priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            deadline
        """,
        (user_id,),
    )

    active_tasks = [dict(row) for row in cursor.fetchall()]

    # Получаем завершённые задачи
    cursor.execute(
        """
        SELECT id, title, description, deadline, priority, is_completed
        FROM tasks
        WHERE user_id = ? AND is_completed = TRUE
        ORDER BY deadline DESC
        LIMIT 10
        """,
        (user_id,),
    )

    completed_tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Сохраняем задачи в кэш
    user_tasks_cache[user_id] = active_tasks

    if not active_tasks and not completed_tasks:
        response = "✅ <b>У вас пока нет задач!</b>\n\n"
        response += "Добавьте первую задачу с помощью кнопки ниже:"

        await callback.message.edit_text(
            response,
            parse_mode="HTML",
        )
        await callback.message.edit_reply_markup(reply_markup=get_tasks_list_keyboard())
    else:
        response = "✅ <b>Ваши задачи:</b>\n\n"

        if active_tasks:
            response += "📋 <b>Активные задачи:</b>\n\n"

            for task in active_tasks:
                title = task["title"]
                response += f"📝 <b>{title}</b>\n"

                if task["deadline"]:
                    response += f"📅 <i>До: {task['deadline']}</i>\n"

                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    task["priority"], "⚪"
                )

                response += f"{priority_emoji} <i>Приоритет: {task['priority']}</i>\n\n"

        if completed_tasks:
            response += "\n🏁 <b>Завершённые задачи:</b>\n\n"

            for task in completed_tasks:
                title = task["title"]
                response += f"✅ <b>{title}</b>\n"

                if task["deadline"]:
                    response += f"📅 <i>Было до: {task['deadline']}</i>\n\n"
                else:
                    response += "\n"

        await callback.message.edit_text(
            response, parse_mode="HTML", disable_web_page_preview=True
        )
        await callback.message.edit_reply_markup(
            reply_markup=get_tasks_selection_keyboard(active_tasks)
        )
