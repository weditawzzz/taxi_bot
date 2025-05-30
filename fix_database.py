#!/usr/bin/env python3
"""
Экстренное исправление базы данных - добавление полей для системы ожидания
"""

import sqlite3
import os
from pathlib import Path


def fix_database_schema():
    """Добавляет отсутствующие поля в таблицу rides"""

    # Путь к базе данных
    db_path = Path("data/database.db")

    if not db_path.exists():
        print("❌ База данных не найдена!")
        return False

    # Подключаемся к базе данных
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("🔧 Исправляем схему базы данных...")

        # Получаем текущую структуру таблицы
        cursor.execute("PRAGMA table_info(rides)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Текущие колонки: {len(existing_columns)}")

        # Список полей для добавления
        fields_to_add = [
            "waiting_started_at TIMESTAMP",
            "waiting_ended_at TIMESTAMP",
            "waiting_minutes INTEGER DEFAULT 0",
            "waiting_cost DECIMAL(10,2) DEFAULT 0.00",
            "stops_log TEXT"
        ]

        added_count = 0
        for field in fields_to_add:
            field_name = field.split()[0]
            if field_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE rides ADD COLUMN {field}")
                    print(f"✅ Добавлено поле: {field_name}")
                    added_count += 1
                except sqlite3.Error as e:
                    print(f"❌ Ошибка добавления {field_name}: {e}")
            else:
                print(f"ℹ️ Поле {field_name} уже существует")

        # Обновляем существующие записи
        if added_count > 0:
            try:
                cursor.execute("""
                               UPDATE rides
                               SET waiting_minutes = 0,
                                   waiting_cost    = 0.00
                               WHERE waiting_minutes IS NULL
                                  OR waiting_cost IS NULL
                               """)
                print("✅ Обновлены существующие записи")
            except sqlite3.Error as e:
                print(f"⚠️ Предупреждение при обновлении: {e}")

        # Подтверждаем изменения
        conn.commit()

        # Проверяем финальную структуру
        cursor.execute("PRAGMA table_info(rides)")
        final_columns = [column[1] for column in cursor.fetchall()]
        print(f"🎉 Финальное количество колонок: {len(final_columns)}")

        print("✅ База данных успешно обновлена!")
        return True

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def remove_problematic_fields_from_model():
    """Временное решение - убираем новые поля из модели если миграция не работает"""

    print("\n🔧 ВРЕМЕННОЕ РЕШЕНИЕ:")
    print("Если миграция не помогла, добавьте в начало core/models.py:")
    print("""
# Временное исправление - комментируем новые поля
class Ride(Base):
    # ... существующие поля ...

    # ВРЕМЕННО ЗАКОММЕНТИРОВАНЫ до миграции БД:
    # waiting_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # waiting_ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True) 
    # waiting_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # waiting_cost: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False, default=Decimal('0.00'))
    # stops_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
""")


if __name__ == "__main__":
    print("🚀 ЭКСТРЕННОЕ ИСПРАВЛЕНИЕ БАЗЫ ДАННЫХ")
    print("=" * 50)

    if fix_database_schema():
        print("\n🎉 ГОТОВО! Перезапустите боты и попробуйте снова.")
    else:
        print("\n❌ Миграция не удалась.")
        remove_problematic_fields_from_model()

    print("=" * 50)