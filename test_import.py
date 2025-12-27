# test_import.py
import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.database import init_database

    print("✅ Импорт database.py успешен")
except ImportError as e:
    print(f"❌ Ошибка импорта database.py: {e}")

try:
    from src.handlers.main import router

    print("✅ Импорт main.py успешен")
except ImportError as e:
    print(f"❌ Ошибка импорта main.py: {e}")

try:
    from src.bot import main

    print("✅ Импорт bot.py успешен")
except ImportError as e:
    print(f"❌ Ошибка импорта bot.py: {e}")
