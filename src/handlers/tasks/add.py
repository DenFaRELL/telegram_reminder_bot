# src/handlers/tasks/add.py - ИСПРАВЛЕННЫЙ

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from src.handlers.tasks.base import (
    save_task,
    validate_deadline,
    validate_description,
    validate_title,
)
from src.keyboards import get_priority_selection_keyboard
from src.states import TaskStates

router = Router()
logger = logging.getLogger(__name__)


# ==================== НАЧАЛО ДОБАВЛЕНИЯ ====================

@router.callback_query(F.data == "add_task_btn")
async def handle_add_task_btn(callback: CallbackQuery, state: FSMContext):
    """Начать добавление задачи через кнопку"""
    try:
        logger.info(f"Начало добавления задачи. Пользователь: {callback.from_user.id}")

        await callback.answer()
        await callback.message.answer(
            "📝 <b>Добавление новой задачи</b>\n\nВведите название задачи:",
            parse_mode="HTML",
        )
        await state.set_state(TaskStates.waiting_for_title)
    except Exception as e:
        logger.error(f"Ошибка в handle_add_task_btn: {e}")
        await callback.answer("❌ Ошибка при добавлении задачи")


# ==================== ОБРАБОТКА ПОЛЕЙ ====================

@router.message(TaskStates.waiting_for_title)
async def handle_task_title(message: Message, state: FSMContext):
    """Обработка названия задачи"""
    try:
        title = message.text.strip()
        logger.info(f"Получено название задачи: {title}")

        is_valid, error_msg = validate_title(title)
        if not is_valid:
            await message.answer(f"❌ <b>{error_msg}</b>", parse_mode="HTML")
            return

        await state.update_data(title=title)
        await message.answer(
            "✅ <b>Название сохранено!</b>\n\n"
            "📝 <b>Введите описание задачи (или напишите 'нет' если не нужно):</b>",
            parse_mode="HTML",
        )
        await state.set_state(TaskStates.waiting_for_description)
    except Exception as e:
        logger.error(f"Ошибка в handle_task_title: {e}")
        await message.answer("❌ Ошибка при обработке названия")


@router.message(TaskStates.waiting_for_description)
async def handle_task_description(message: Message, state: FSMContext):
    """Обработка описания задачи"""
    try:
        description = message.text.strip()
        logger.info(f"Получено описание задачи: {description[:50]}...")

        is_valid, error_msg = validate_description(description)
        if not is_valid:
            await message.answer(f"❌ <b>{error_msg}</b>", parse_mode="HTML")
            return

        if description.lower() == "нет" or not description:
            description = None

        await state.update_data(description=description)
        await message.answer(
            "✅ <b>Описание сохранено!</b>\n\n"
            "📅 <b>Введите дедлайн задачи (формат: ГГГГ-ММ-ДД, или напишите 'нет'):</b>\n"
            "<i>Пример: 2024-12-31</i>",
            parse_mode="HTML",
        )
        await state.set_state(TaskStates.waiting_for_deadline)
    except Exception as e:
        logger.error(f"Ошибка в handle_task_description: {e}")
        await message.answer("❌ Ошибка при обработке описания")


@router.message(TaskStates.waiting_for_deadline)
async def handle_task_deadline(message: Message, state: FSMContext):
    """Обработка дедлайна задачи"""
    try:
        deadline = message.text.strip()
        logger.info(f"Получен дедлайн задачи: {deadline}")

        is_valid, error_msg = validate_deadline(deadline)
        if not is_valid:
            await message.answer(f"❌ <b>{error_msg}</b>", parse_mode="HTML")
            return

        if deadline.lower() == "нет" or not deadline:
            deadline = None

        await state.update_data(deadline=deadline)
        await message.answer(
            "✅ <b>Дедлайн сохранён!</b>\n\n"
            "🎯 <b>Выберите приоритет задачи:</b>",
            reply_markup=get_priority_selection_keyboard(for_edit=False),
            parse_mode="HTML",
        )
        await state.set_state(TaskStates.waiting_for_priority)
    except Exception as e:
        logger.error(f"Ошибка в handle_task_deadline: {e}")
        await message.answer("❌ Ошибка при обработке дедлайна")


# ==================== ВЫБОР ПРИОРИТЕТА ====================

@router.callback_query(TaskStates.waiting_for_priority, F.data.startswith("select_priority_"))
async def handle_select_priority_for_new(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора приоритета для новой задачи"""
    try:
        priority = callback.data.split("_")[2]
        logger.info(f"Выбран приоритет для новой задачи: {priority}")

        await callback.answer(f"Выбран приоритет: {priority}")

        # Получаем все данные из состояния
        data = await state.get_data()
        user_id = callback.from_user.id

        # Сохраняем задачу
        success, task_id, msg = save_task(user_id, {**data, "priority": priority})

        if success:
            response = "🎉 <b>Задача успешно добавлена!</b>\n\n"
            response += f"📝 <b>Название:</b> {data['title']}\n"

            if data.get("description"):
                response += f"📄 <b>Описание:</b> {data['description']}\n"

            if data.get("deadline"):
                response += f"📅 <b>Дедлайн:</b> {data['deadline']}\n"

            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            response += f"🎯 <b>Приоритет:</b> {priority_emoji.get(priority, '⚪')} {priority}\n"

            # Кнопка для возврата к задачам
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Вернуться к задачам",
                            callback_data="back_to_tasks"
                        )
                    ]
                ]
            )

            await callback.message.answer(
                response, reply_markup=keyboard, parse_mode="HTML"
            )
        else:
            await callback.message.answer(f"❌ <b>{msg}</b>", parse_mode="HTML")

        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка в handle_select_priority_for_new: {e}")
        await callback.answer("❌ Ошибка при сохранении задачи")
        await state.clear()
