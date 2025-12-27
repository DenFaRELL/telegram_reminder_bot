# run.py
import asyncio
import os
import sys

# Добавляем корневую директорию в sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.database import fix_invalid_dates, init_database

# Инициализируем базу данных
init_database()
fix_invalid_dates()

# Теперь импортируем main после установки путей
from src.bot import main

if __name__ == "__main__":
    asyncio.run(main())
