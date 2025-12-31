"""Запуск всех тестов"""

import os
import sys


def main():
    print("Запуск тестов Telegram бота напоминаний...")
    print("=" * 50)

    # Добавляем текущую директорию в путь
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)

    # Импортируем и запускаем тесты
    try:
        import tests.test_all as test_module

        # Проверяем, есть ли функция run_all_tests
        if hasattr(test_module, "__file__"):
            print(f"Запуск тестов из: {test_module.__file__}")

        # Запускаем pytest напрямую
        import pytest

        exit_code = pytest.main(
            [
                "tests/test_all.py",
                "-v",
                "--tb=short",
                "--disable-warnings",
                "--no-header",
                "-q",
            ]
        )

    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("Проверьте, что файл tests/test_all.py существует и корректный")
        exit_code = 1
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        exit_code = 1

    print("=" * 50)

    if exit_code == 0:
        print("✅ Все тесты пройдены успешно!")
    else:
        print("❌ Некоторые тесты не пройдены")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
