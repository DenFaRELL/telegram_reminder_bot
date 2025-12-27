# test_database.py
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Проверяем содержимое файла database.py
database_path = os.path.join(os.path.dirname(__file__), "src", "database.py")
print(f"Проверяем файл: {database_path}")

if os.path.exists(database_path):
    with open(database_path, "r", encoding="utf-8") as f:
        content = f.read()

    print("Содержимое файла database.py:")
    print("-" * 50)
    print(content[:500])  # Первые 500 символов
    print("-" * 50)

    # Проверяем наличие функций
    if "def fix_invalid_dates" in content:
        print("✅ Функция fix_invalid_dates найдена в файле")
    else:
        print("❌ Функция fix_invalid_dates НЕ найдена в файле")

    if "def init_database" in content:
        print("✅ Функция init_database найдена в файле")
    else:
        print("❌ Функция init_database НЕ найдена в файле")

    # Попробуем импортировать
    try:
        from src.database import fix_invalid_dates, init_database

        print("✅ Импорт функций успешен")
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
else:
    print(f"❌ Файл {database_path} не существует!")
