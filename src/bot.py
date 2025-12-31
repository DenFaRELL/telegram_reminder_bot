# src/bot.py
import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("BOT_TOKEN не найден в переменных окружения!")
    exit(1)

# Создаем экземпляры бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Импортируем и подключаем роутеры
try:
    from src.handlers import events_router, main_router, schedule_router, tasks_router

    dp.include_router(main_router)
    dp.include_router(schedule_router)
    dp.include_router(tasks_router)
    dp.include_router(events_router)

    logging.info("✅ Роутеры успешно подключены")

except ImportError as e:
    logging.error(f"❌ Ошибка импорта роутеров: {e}")
    logging.error("Проверьте структуру файлов и импорты")
    sys.exit(1)


# В функции on_startup():
async def on_startup():
    """Действия при запуске бота"""
    logging.info("🚀 Запуск сервисов напоминаний...")

    # Инициализируем и запускаем сервисы напоминаний
    from src.event_reminders import get_event_reminder_service
    from src.task_reminders import get_task_reminder_service

    try:
        # Сервис напоминаний о событиях
        event_reminder_service = get_event_reminder_service(bot)
        if event_reminder_service:
            asyncio.create_task(event_reminder_service.start())
            logging.info("✅ Сервис напоминаний о событиях запущен")

            # Запускаем немедленную проверку для отладки
            asyncio.create_task(event_reminder_service.check_upcoming_events())
            logging.info("🔍 Запущена проверка предстоящих событий")

        # Сервис напоминаний о задачах
        task_reminder_service = get_task_reminder_service(bot)
        if task_reminder_service:
            asyncio.create_task(task_reminder_service.start())
            logging.info("✅ Сервис напоминаний о задачах запущен")

            # Запускаем немедленную проверку для отладки
            asyncio.create_task(task_reminder_service.check_upcoming_deadlines())
            logging.info("🔍 Запущена проверка предстоящих дедлайнов")

    except Exception as e:
        logging.error(f"❌ Ошибка при запуске сервисов напоминаний: {e}", exc_info=True)


async def on_shutdown():
    """Действия при остановке бота"""
    logging.info("🛑 Остановка сервисов напоминаний...")

    try:
        from src.event_reminders import get_event_reminder_service
        from src.task_reminders import get_task_reminder_service

        # Останавливаем сервис напоминаний о событиях
        event_reminder_service = get_event_reminder_service()
        if event_reminder_service and event_reminder_service.running:
            await event_reminder_service.stop()
            logging.info("✅ Сервис напоминаний о событиях остановлен")

        # Останавливаем сервис напоминаний о задачах
        task_reminder_service = get_task_reminder_service()
        if task_reminder_service and task_reminder_service.running:
            await task_reminder_service.stop()
            logging.info("✅ Сервис напоминаний о задачах остановлен")

    except Exception as e:
        logging.error(f"❌ Ошибка при остановке сервисов напоминаний: {e}")


async def main():
    """Основная функция запуска бота"""
    logging.info("Бот запускается...")

    # Регистрируем обработчики запуска и остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
