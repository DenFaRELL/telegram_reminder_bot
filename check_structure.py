# check_structure.py
import os


def check_structure():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    required_files = [
        "run.py",
        "src/__init__.py",
        "src/bot.py",
        "src/database.py",
        "src/keyboards.py",
        "src/states.py",
        "src/handlers/__init__.py",
        "src/handlers/main.py",
        "src/handlers/schedule.py",
        "src/handlers/tasks.py",
        "src/handlers/events.py",
    ]

    print("Проверка структуры проекта:")
    print("=" * 50)

    for file in required_files:
        path = os.path.join(base_dir, file)
        if os.path.exists(path):
            print(f"✓ {file}")
        else:
            print(f"✗ {file} - НЕ НАЙДЕН")

    print("=" * 50)


if __name__ == "__main__":
    check_structure()
