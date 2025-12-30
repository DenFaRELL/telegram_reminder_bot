# src/handlers/tasks/edit.py
"""Обработчики для редактирования и удаления задач"""

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from src.handlers.tasks.base import (
    delete_task,
    format_task_details,
    get_task,
    update_task,
    validate_deadline,
    validate_description,
    validate_priority,
    validate_title,
)
from src.keyboards import (
    get_delete_task_confirmation_keyboard,
    get_edit_task_keyboard,
    get_priority_selection_keyboard,
    get_task_detail_keyboard,
)
from src.states import EditTaskStates

router = Router()
logger = logging.getLogger(__name__)


# ==================== РЕДАКТИРОВАНИЕ ====================


@router.callback_query(F.data.startswith("edit_task_"))
async def handle_edit_task(callback: CallbackQuery):
    """Показать меню редактирования задачи"""
    try:
        logger.info(f"callback_data в handle_edit_task: {callback.data}")
        # Формат: edit_task_17
        data_parts = callback.data.split("_")
        if len(data_parts) != 3:
            await callback.answer("❌ Неверный формат")
            return

        task_id = int(data_parts[2])  # '17'
        logger.info(f"Запрос на редактирование задачи ID: {task_id}")

        await callback.answer()

        task = get_task(task_id)
        if not task:
            await callback.message.answer("❌ Задача не найдена!")
            return

        response = format_task_details(task)
        response += "\n<b>Выберите что изменить:</b>"

        await callback.message.answer(
            response,
            reply_markup=get_edit_task_keyboard(task_id),
            parse_mode="HTML"
        )
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга в handle_edit_task: {e}, callback_data: {callback.data}")
        await callback.answer("❌ Ошибка при редактировании")
    except Exception as e:
        logger.error(f"Ошибка в handle_edit_task: {e}")
        await callback.answer("❌ Ошибка при редактировании")


# ==================== УДАЛЕНИЕ ====================


@router.callback_query(F.data.startswith("delete_task_"))
async def handle_delete_task(callback: CallbackQuery):
    """Показать подтверждение удаления задачи"""
    try:
        task_id = int(callback.data.split("_")[2])
        logger.info(f"Запрос на удаление задачи ID: {task_id}")

        await callback.answer()

        task = get_task(task_id)
        if not task:
            await callback.message.answer("❌ Задача не найдена!")
            return

        response = f"🗑️ <b>Удаление задачи:</b>\n\n"
        response += f"📝 <b>Название:</b> {task['title']}\n"

        if task.get("description"):
            response += f"📄 <b>Описание:</b> {task['description']}\n"

        if task.get("deadline"):
            response += f"📅 <b>Дедлайн:</b> {task['deadline']}\n"

        response += "\n<b>Вы действительно хотите удалить эту задачу?</b>"

        await callback.message.answer(
            response,
            reply_markup=get_delete_task_confirmation_keyboard(task_id),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Ошибка в handle_delete_task: {e}")
        await callback.answer("❌ Ошибка при удалении")


@router.callback_query(F.data.startswith("confirm_delete_task_"))
async def handle_confirm_delete_task(callback: CallbackQuery):
    """Подтверждение и выполнение удаления задачи"""
    try:
        task_id = int(callback.data.split("_")[3])
        logger.info(f"Подтверждение удаления задачи ID: {task_id}")

        await callback.answer()

        success = delete_task(task_id)
        if success:
            await callback.message.answer("✅ Задача удалена!")

            # Показываем обновленный список задач
            user_id = callback.from_user.id
            from .view import show_tasks_list

            await show_tasks_list(callback.message, user_id)
        else:
            await callback.message.answer("❌ Не удалось удалить задачу")
    except Exception as e:
        logger.error(f"Ошибка в handle_confirm_delete_task: {e}")
        await callback.answer("❌ Ошибка при удалении")


# ==================== РЕДАКТИРОВАНИЕ ПОЛЕЙ ====================


# src/handlers/tasks/edit.py - ПЕРЕПИШИТЕ handle_edit_task_field

@router.callback_query(F.data.startswith("edit_task_field_"))
async def handle_edit_task_field(callback: CallbackQuery, state: FSMContext):
    """Выбрано поле задачи для редактирования"""
    try:
        logger.info(f"Получен callback_data: {callback.data}")

        # Формат callback_data: edit_task_field_title_17
        # Разделяем на: ['edit', 'task', 'field', 'title', '17']
        data_parts = callback.data.split("_")

        logger.info(f"Разделенные части: {data_parts}, количество: {len(data_parts)}")

        if len(data_parts) < 5:
            logger.error(f"Неверный формат callback_data: {callback.data}")
            await callback.answer("❌ Неверный формат callback_data")
            return

        # Четвертый элемент после 'edit_task_field_' - это название поля
        # Например: edit_task_field_title_17 → parts[3] = 'title'
        field_name = data_parts[3]  # 'title', 'description', 'deadline', 'priority'
        task_id = int(data_parts[4])  # '17'

        logger.info(f"Парсинг успешен: поле={field_name}, task_id={task_id}")

        await callback.answer()
        await state.update_data(task_id=task_id, field_name=field_name)

        task = get_task(task_id)
        if not task:
            await callback.message.answer("❌ Задача не найдена!")
            return

        if field_name == "priority":
            await callback.message.answer(
                "🎯 <b>Выберите новый приоритет задачи:</b>",
                reply_markup=get_priority_selection_keyboard(
                    for_edit=True, task_id=task_id
                ),
                parse_mode="HTML",
            )
        else:
            field_names = {
                "title": "название задачи",
                "description": "описание задачи (или 'нет' если не нужно)",
                "deadline": "дедлайн задачи (формат: ГГГГ-ММ-ДД, или 'нет')",
            }

            if field_name not in field_names:
                logger.error(f"Неизвестное поле: {field_name}")
                await callback.answer(f"❌ Неизвестное поле: {field_name}")
                return

            current_value = task.get(field_name, "")

            await callback.message.answer(
                f"✏️ <b>Редактирование {field_names[field_name]}</b>\n\n"
                f"Текущее значение: <code>{current_value if current_value else 'не указано'}</code>\n\n"
                f"<b>Введите новое значение:</b>",
                parse_mode="HTML",
            )
            await state.set_state(EditTaskStates.waiting_for_field_value)

    except ValueError as e:
        logger.error(f"Ошибка преобразования числа в handle_edit_task_field: {e}, callback_data: {callback.data}")
        await callback.answer("❌ Ошибка: неверный ID задачи")
    except IndexError as e:
        logger.error(f"Ошибка индекса в handle_edit_task_field: {e}, callback_data: {callback.data}, parts: {data_parts if 'data_parts' in locals() else 'N/A'}")
        await callback.answer("❌ Ошибка: неверный формат данных")
    except Exception as e:
        logger.error(f"Ошибка в handle_edit_task_field: {e}, callback_data: {callback.data}")
        await callback.answer("❌ Ошибка при редактировании поля")


@router.callback_query(F.data.startswith("select_priority_"))
async def handle_select_priority_for_edit(callback: CallbackQuery):
    """Выбран новый приоритет задачи (только для редактирования)"""
    try:
        # Формат callback_data: select_priority_high_17 (для редактирования)
        data_parts = callback.data.split("_")

        if len(data_parts) > 3:  # Значит есть task_id
            # Должно быть: ['select', 'priority', 'high', '17']
            if len(data_parts) != 4:
                await callback.answer("❌ Неверный формат callback_data")
                return

            new_priority = data_parts[2]  # 'high', 'medium', 'low'
            task_id = int(data_parts[3])  # '17'

            # Проверяем, что приоритет валидный
            valid_priorities = ['high', 'medium', 'low']
            if new_priority not in valid_priorities:
                await callback.answer(f"❌ Неверный приоритет: {new_priority}")
                return

            logger.info(f"Выбор приоритета {new_priority} для задачи ID: {task_id}")

            await callback.answer(f"Выбран приоритет: {new_priority}")

            success, msg = update_task(task_id, "priority", new_priority)
            if success:
                await callback.message.answer(
                    f"✅ <b>Приоритет задачи изменён на {new_priority}!</b>",
                    parse_mode="HTML",
                )

                # Показываем обновленную задачу
                task = get_task(task_id)
                if task:
                    response = format_task_details(task)
                    await callback.message.answer(
                        response,
                        reply_markup=get_task_detail_keyboard(task_id),
                        parse_mode="HTML",
                    )
            else:
                await callback.message.answer(f"❌ <b>{msg}</b>", parse_mode="HTML")
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга в handle_select_priority_for_edit: {e}, callback_data: {callback.data}")
        await callback.answer("❌ Ошибка при выборе приоритета")
    except Exception as e:
        logger.error(f"Ошибка в handle_select_priority_for_edit: {e}")
        await callback.answer("❌ Ошибка при выборе приоритета")


@router.message(EditTaskStates.waiting_for_field_value)
async def handle_task_field_value_input(message: Message, state: FSMContext):
    """Обработка нового значения поля задачи"""
    try:
        data = await state.get_data()
        task_id = data["task_id"]
        field_name = data["field_name"]
        new_value = message.text.strip()

        logger.info(f"Ввод нового значения для поля {field_name} задачи ID: {task_id}")

        # Валидация в зависимости от поля
        is_valid = True
        error_msg = ""

        if field_name == "title":
            is_valid, error_msg = validate_title(new_value)
        elif field_name == "description":
            is_valid, error_msg = validate_description(new_value)
            if is_valid and (not new_value or new_value.lower() == "нет"):
                new_value = None
        elif field_name == "deadline":
            if new_value.lower() == "нет" or not new_value:
                new_value = None
            else:
                is_valid, error_msg = validate_deadline(new_value)
        else:
            is_valid, error_msg = False, "Неизвестное поле"

        if not is_valid:
            await message.answer(f"❌ <b>{error_msg}</b>", parse_mode="HTML")
            return

        # Обновляем задачу
        success, msg = update_task(task_id, field_name, new_value)

        if success:
            field_display_names = {
                "title": "Название задачи",
                "description": "Описание задачи",
                "deadline": "Дедлайн задачи",
            }

            await message.answer(
                f"✅ <b>{field_display_names[field_name]} успешно обновлено!</b>",
                parse_mode="HTML",
            )

            # Показываем обновленную задачу
            task = get_task(task_id)
            if task:
                response = format_task_details(task)
                await message.answer(
                    response,
                    reply_markup=get_task_detail_keyboard(task_id),
                    parse_mode="HTML",
                )
        else:
            await message.answer(f"❌ <b>{msg}</b>", parse_mode="HTML")

        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка в handle_task_field_value_input: {e}")
        await message.answer("❌ Произошла ошибка при обновлении")
        await state.clear()


# ==================== ЗАВЕРШЕНИЕ ЗАДАЧИ ====================


@router.callback_query(F.data.startswith("complete_task_"))
async def handle_complete_task(callback: CallbackQuery):
    """Завершить задачу"""
    try:
        task_id = int(callback.data.split("_")[2])
        logger.info(f"Завершение задачи ID: {task_id}")

        await callback.answer()

        success, msg = update_task(task_id, "complete", True)
        if success:
            await callback.message.answer("✅ Задача завершена!")

            # Показываем обновленный список задач
            user_id = callback.from_user.id
            from .view import show_tasks_list

            await show_tasks_list(callback.message, user_id)
        else:
            await callback.message.answer(f"❌ <b>{msg}</b>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка в handle_complete_task: {e}")
        await callback.answer("❌ Ошибка при завершении задачи")
