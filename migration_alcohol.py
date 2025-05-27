#!/usr/bin/env python3
"""
Скрипт миграции базы данных для добавления поля budget в таблицу Order
Запустите этот скрипт для обновления существующей базы данных
"""

import sqlite3
import os
from pathlib import Path


def migrate_database():
    """Добавляет поле budget в существующую базу данных"""

    # Путь к базе данных
    db_path = Path("data/database.db")

    # Создаем папку data если не существует
    db_path.parent.mkdir(exist_ok=True)

    # Подключаемся к базе данных
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("🔄 Начинаем миграцию базы данных для алкоголя...")

        # Проверяем существование таблицы orders
        cursor.execute("""
                       SELECT name
                       FROM sqlite_master
                       WHERE type = 'table'
                         AND name = 'orders'
                       """)

        if not cursor.fetchone():
            print("❌ Таблица orders не найдена. Запустите сначала основное приложение.")
            return False

        # Получаем существующие колонки
        cursor.execute("PRAGMA table_info(orders)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Существующие колонки: {existing_columns}")

        # Добавляем поле budget если его нет
        if 'budget' not in existing_columns:
            try:
                cursor.execute("ALTER TABLE orders ADD COLUMN budget REAL")
                print("✅ Добавлена колонка: budget")
            except sqlite3.Error as e:
                print(f"❌ Ошибка добавления колонки budget: {e}")
        else:
            print("ℹ️ Колонка budget уже существует")

        # Подтверждаем изменения
        conn.commit()

        # Проверяем финальную структуру
        cursor.execute("PRAGMA table_info(orders)")
        final_columns = [column[1] for column in cursor.fetchall()]
        print(f"🎉 Финальная структура таблицы: {final_columns}")

        print("✅ Миграция базы данных завершена успешно!")
        return True

    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def verify_migration():
    """Проверяет успешность миграции"""
    db_path = Path("data/database.db")

    if not db_path.exists():
        print("❌ База данных не найдена")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Проверяем наличие поля budget
        cursor.execute("PRAGMA table_info(orders)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'budget' not in columns:
            print("❌ Отсутствует колонка: budget")
            return False
        else:
            print("✅ Колонка budget присутствует")
            return True

    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    print("🚀 Запуск миграции базы данных для системы доставки алкоголя")
    print("=" * 60)

    # Выполняем миграцию
    if migrate_database():
        print()
        print("🔍 Проверяем результат миграции...")
        if verify_migration():
            print()
            print("🎉 Миграция завершена успешно!")
            print("✅ Теперь вы можете использовать новую функцию доставки алкоголя")
        else:
            print("❌ Проверка миграции не пройдена")
    else:
        print("❌ Миграция не выполнена")

    print("=" * 60)