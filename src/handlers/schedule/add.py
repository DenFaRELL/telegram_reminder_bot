# src/handlers/schedule/add.py - ПЕРЕДЕЛАННАЯ ВЕРСИЯ
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.states import AddLessonStates

router = Router()


@router.callback_query(F.data == "add_lesson_btn")
async def add_lesson_start(callback: CallbackQuery, state: FSMContext):
    """Начать процесс добавления урока"""
    from src.keyboards import get_add_lesson_keyboard

    await callback.message.delete()
    await callback.message.answer(
        "📝 <b>Добавление нового урока</b>\n\nВыберите день недели:",
        reply_markup=get_add_lesson_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("add_lesson_day_"))
async def process_day_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора дня недели"""
    day = callback.data.replace("add_lesson_day_", "")

    await state.update_data(day=day)
    await callback.message.delete()

    await callback.message.answer(
        f"📅 <b>Выбран день:</b> {day}\n\n"
        "📚 <b>Введите название предмета:</b>\n"
        "<i>Например: Математика, Физика, Программирование</i>",
        parse_mode="HTML",
    )

    await state.set_state(AddLessonStates.waiting_for_subject)
    await callback.answer(f"Выбран: {day}")


@router.message(AddLessonStates.waiting_for_subject)
async def process_subject(message: Message, state: FSMContext):
    """Обработка названия предмета"""
    from src.handlers.schedule.base import validate_subject

    subject = message.text.strip()
    is_valid, error = validate_subject(subject)

    if not is_valid:
        await message.answer(f"❌ {error}", parse_mode="HTML")
        return

    await state.update_data(subject=subject)
    await message.answer(
        "✅ <b>Предмет сохранён!</b>\n\n"
        "⏰ <b>Теперь введите время занятия:</b>\n"
        "<i>Формат: ЧЧ:ММ-ЧЧ:ММ (например: 08:30-10:05)</i>",
        parse_mode="HTML",
    )

    await state.set_state(AddLessonStates.waiting_for_time)


@router.message(AddLessonStates.waiting_for_time)
async def process_time(message: Message, state: FSMContext):
    """Обработка времени занятия"""
    from src.handlers.schedule.base import validate_time

    time_input = message.text.strip()
    is_valid, error, times = validate_time(time_input)

    if not is_valid:
        await message.answer(f"❌ {error}", parse_mode="HTML")
        return

    start_time, end_time = times
    await state.update_data(start_time=start_time, end_time=end_time)

    await message.answer(
        "✅ <b>Время сохранено!</b>\n\n"
        "🏢 <b>Введите номер корпуса:</b>\n"
        "<i>Только цифры, или напишите 'нет'</i>",
        parse_mode="HTML",
    )

    await state.set_state(AddLessonStates.waiting_for_build)


@router.message(AddLessonStates.waiting_for_build)
async def process_build(message: Message, state: FSMContext):
    """Обработка номера корпуса"""
    from src.handlers.schedule.base import validate_build

    build = message.text.strip()
    is_valid, error = validate_build(build)

    if not is_valid:
        await message.answer(f"❌ {error}", parse_mode="HTML")
        return

    # Обработка "нет"
    if build.lower() == "нет":
        build = None

    await state.update_data(build=build)

    await message.answer(
        f"✅ <b>Корпус сохранён: {build if build else 'не указан'}</b>\n\n"
        "🚪 <b>Введите номер аудитории:</b>\n"
        "<i>Только цифры, или напишите 'нет'</i>",
        parse_mode="HTML",
    )

    await state.set_state(AddLessonStates.waiting_for_room)


@router.message(AddLessonStates.waiting_for_room)
async def process_room(message: Message, state: FSMContext):
    """Обработка номера аудитории"""
    from src.handlers.schedule.base import validate_room

    room = message.text.strip()
    is_valid, error = validate_room(room)

    if not is_valid:
        await message.answer(f"❌ {error}", parse_mode="HTML")
        return

    # Обработка "нет"
    if room.lower() == "нет":
        room = None

    await state.update_data(room=room)

    await message.answer(
        f"✅ <b>Аудитория сохранена: {room if room else 'не указана'}</b>\n\n"
        "👨‍🏫 <b>Введите ФИО преподавателя:</b>\n"
        "<i>Например: Иванов И.И., или напишите 'нет'</i>",
        parse_mode="HTML",
    )

    await state.set_state(AddLessonStates.waiting_for_teacher)


@router.message(AddLessonStates.waiting_for_teacher)
async def process_teacher(message: Message, state: FSMContext):
    """Обработка преподавателя и завершение добавления"""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from src.handlers.schedule.base import save_lesson, validate_teacher

    teacher = message.text.strip()
    is_valid, error = validate_teacher(teacher)

    if not is_valid:
        await message.answer(f"❌ {error}", parse_mode="HTML")
        return

    # Обработка "нет"
    if teacher.lower() == "нет":
        teacher = None

    # Получаем все данные
    data = await state.get_data()
    user_id = message.from_user.id

    # Сохраняем урок
    success, lesson_id, msg = save_lesson(user_id, data)

    if success:
        # Формируем ответ
        response = "🎉 <b>Урок успешно добавлен!</b>\n\n"
        response += f"📅 <b>День:</b> {data['day']}\n"
        response += f"📚 <b>Предмет:</b> {data['subject']}\n"
        response += f"🕒 <b>Время:</b> {data['start_time']} - {data['end_time']}\n"

        if data.get("build"):
            response += f"🏢 <b>Корпус:</b> {data['build']}\n"
        if data.get("room"):
            response += f"🚪 <b>Аудитория:</b> {data['room']}\n"
        if teacher:
            response += f"👨‍🏫 <b>Преподаватель:</b> {teacher}\n"

        # Кнопка возврата
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📅 Вернуться к расписанию",
                        callback_data="back_to_schedule",
                    )
                ]
            ]
        )

        await message.answer(response, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(f"❌ <b>Ошибка:</b> {msg}", parse_mode="HTML")

    # Очищаем состояние
    await state.clear()
