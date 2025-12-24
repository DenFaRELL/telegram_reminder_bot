# run.py
import sys
import os

# Добавляем корневую директорию проекта в путь Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Теперь запускаем бота
if __name__ == "__main__":
    # Импортируем и запускаем асинхронно
    import asyncio
    from src.bot import main
    asyncio.run(main())