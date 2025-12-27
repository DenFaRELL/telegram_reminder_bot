# check_files.py
import os


def check_files():
    base = os.path.dirname(os.path.abspath(__file__))

    files = [
        ("run.py", "run.py"),
        (".env", ".env (файл с токеном бота)"),
        ("src/__init__.py", "src/__init__.py"),
        ("src/bot.py", "src/bot.py"),
        ("src/database.py", "src/database.py"),
        ("src/keyboards.py", "src/keyboards.py"),
        ("src/states.py", "src/states.py"),
        ("src/handlers/__init__.py", "src/handlers/__init__.py"),
        ("src/handlers/main.py", "src/handlers/main.py"),
        ("src/handlers/schedule.py", "src/handlers/schedule.py"),
        ("src/handlers/tasks.py", "src/handlers/tasks.py"),
        ("src/handlers/events.py", "src/handlers/events.py"),
    ]

    print("Проверка файлов проекта:")
    print("=" * 60)

    all_ok = True
    for file_path, description in files:
        full_path = os.path.join(base, file_path)
        if os.path.exists(full_path):
            print(f"✓ {description}")
        else:
            print(f"✗ {description} - НЕ НАЙДЕН")
            all_ok = False

    print("=" * 60)

    if all_ok:
        print("✅ Все файлы на месте!")
    else:
        print("❌ Некоторые файлы отсутствуют. Создайте их.")


if __name__ == "__main__":
    check_files()
