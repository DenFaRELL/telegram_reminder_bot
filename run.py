# run.py
import asyncio
import os
import sys

# Добавляем корневую директорию в sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.bot import main

if __name__ == "__main__":
    asyncio.run(main())
