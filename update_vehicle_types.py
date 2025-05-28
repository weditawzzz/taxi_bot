#!/usr/bin/env python3
"""
Скрипт миграции для обновления типов автомобилей
ИСПРАВЛЯЕТ: Lancer Sportback → Hatchback, добавляет новые типы
"""

import sqlite3
import os
from pathlib import Path
from collections import Counter


def detect_vehicle_type_migration(make: str, model: str) -> str:
    """
    Функция определения типа кузова для миграции (упрощенная версия)

    Args:
        make: Марка автомобиля
        model: Полная модель

    Returns:
        str: Тип кузова
    """
    if not make or not model:
        return "SEDAN"

    make_lower = make.lower() if make else ""
    model_lower = model.lower() if model else ""
    full_name = f"{make_lower} {model_lower}"

    print(f"🔍 Analyzing: {make} {model} -> {full_name}")

    # Универсалы / Wagon / Комби
    wagon_keywords = [
        'touring', 'estate', 'wagon', 'kombi', 'avant', 'variant', 'sw', 'break',
        'sportwagon', 'allroad', 'outback', 'cross country'
    ]
    if any(keyword in model_lower for keyword in wagon_keywords):
        print(f"  ✅ Detected: WAGON (keyword match)")
        return "WAGON"

    # Внедорожники / SUV (большие)
    suv_keywords = [
        'x5', 'x7', 'q7', 'q8', 'gle', 'gls', 'cayenne', 'touareg', 'tahoe',
        'escalade', 'navigator', 'expedition', 'suburban', 'yukon', 'range rover',
        'discovery', 'defender'
    ]
    if any(keyword in model_lower for keyword in suv_keywords):
        print(f"  ✅ Detected: SUV (keyword match)")
        return "SUV"

    # Кроссоверы (компактные SUV)
    crossover_keywords = [
        'x1', 'x3', 'q3', 'q5', 'glb', 'glc', 'macan', 'tiguan', 'rav4', 'cr-v',
        'qashqai', 'juke', 'captur', 'tucson', 'sportage', 'cx-5', 'forester',
        'xv', 'impreza', 'crossover', 'cross'
    ]
    if any(keyword in model_lower for keyword in crossover_keywords):
        print(f"  ✅ Detected: CROSSOVER (keyword match)")
        return "CROSSOVER"

    # Фургоны / Van
    van_keywords = [
        'van', 'transporter', 'sprinter', 'ducato', 'transit', 'crafter',
        'daily', 'master', 'movano', 'boxer'
    ]
    if any(keyword in model_lower for keyword in van_keywords):
        print(f"  ✅ Detected: VAN (keyword match)")
        return "VAN"

    # Минивэны / MPV
    mpv_keywords = [
        'mpv', 'zafira', 'sharan', 'galaxy', 'espace', 'scenic', 'touran',
        'verso', 'carens', 'stream', 'odyssey', 'previa'
    ]
    if any(keyword in model_lower for keyword in mpv_keywords):
        print(f"  ✅ Detected: MPV (keyword match)")
        return "MPV"

    # Купе и кабриолеты
    coupe_keywords = [
        'coupe', 'coupé', 'cabrio', 'convertible', 'roadster', 'spider', 'spyder',
        'targa', 'z4', 'slk', 'slc', 'tt', 'boxster'
    ]
    if any(keyword in model_lower for keyword in coupe_keywords):
        if any(keyword in model_lower for keyword in ['cabrio', 'convertible', 'roadster', 'spider', 'spyder']):
            print(f"  ✅ Detected: CONVERTIBLE (keyword match)")
            return "CONVERTIBLE"
        else:
            print(f"  ✅ Detected: COUPE (keyword match)")
            return "COUPE"

    # Хэтчбеки (включая спортбэки) - ИСПРАВЛЕНО!
    hatchback_keywords = [
        'hatchback', 'golf', 'polo', 'corsa', 'fiesta', 'focus', 'astra', 'civic',
        'i20', 'i30', 'rio', 'ceed', 'ibiza', 'leon', 'fabia', 'swift',
        'sportback', 'back'  # ИСПРАВЛЕНО: Sportback тоже хэтчбек
    ]

    # Специальная проверка для Lancer Sportback - ИСПРАВЛЕНИЕ ОШИБКИ!
    if 'lancer' in model_lower and 'sportback' in model_lower:
        print(f"  ✅ Detected: HATCHBACK (Lancer Sportback fix)")
        return "HATCHBACK"

    if any(keyword in model_lower for keyword in hatchback_keywords):
        print(f"  ✅ Detected: HATCHBACK (keyword match)")
        return "HATCHBACK"

    # Пикапы
    pickup_keywords = [
        'pickup', 'pick-up', 'navara', 'hilux', 'ranger', 'amarok', 'l200',
        'frontier', 'ridgeline', 'colorado', 'canyon'
    ]
    if any(keyword in model_lower for keyword in pickup_keywords):
        print(f"  ✅ Detected: PICKUP (keyword match)")
        return "PICKUP"

    # Электромобили
    electric_keywords = [
        'tesla', 'electric', 'hybrid', 'prius', 'leaf', 'zoe', 'e-golf',
        'i3', 'i8', 'model s', 'model 3', 'model x', 'model y'
    ]
    if any(keyword in full_name for keyword in electric_keywords):
        print(f"  ✅ Detected: ELECTRIC (keyword match)")
        return "ELECTRIC"

    # Премиум марки (люкс)
    luxury_makes = [
        'mercedes', 'bmw', 'audi', 'lexus', 'jaguar', 'porsche', 'bentley',
        'rolls-royce', 'maserati', 'ferrari', 'lamborghini', 'aston martin'
    ]

    # Премиум модели
    luxury_models = [
        's-class', 'e-class', '7 series', 'a8', 'ls', 'xj', 'panamera',
        'quattroporte', 'continental', 'phantom', 'ghost'
    ]

    if (make_lower in luxury_makes and any(keyword in model_lower for keyword in luxury_models)) or \
            any(keyword in full_name for keyword in ['s-class', 'phantom', 'continental gt']):
        print(f"  ✅ Detected: LUXURY (premium match)")
        return "LUXURY"

    # По умолчанию - седан
    print(f"  ➡️ Default: SEDAN")
    return "SEDAN"


def get_seats_by_type_migration(vehicle_type: str) -> int:
    """Определение количества мест по типу кузова для миграции"""
    seats_mapping = {
        'COUPE': 2,
        'CONVERTIBLE': 2,
        'SEDAN': 4,
        'HATCHBACK': 4,
        'WAGON': 5,
        'CROSSOVER': 5,
        'SUV': 7,
        'MPV': 7,
        'VAN': 8,
        'PICKUP': 4,
        'ELECTRIC': 4,
        'LUXURY': 4
    }

    return seats_mapping.get(vehicle_type, 4)


def migrate_vehicle_types():
    """Главная функция миграции"""

    # Путь к базе данных
    db_path = Path("data/database.db")

    if not db_path.exists():
        print("❌ База данных не найдена. Создайте её сначала.")
        return False

    print("🚀 Начинаем миграцию типов автомобилей...")
    print("=" * 60)

    # Подключаемся к базе данных
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Проверяем существование таблицы vehicles
        cursor.execute("""
                       SELECT name
                       FROM sqlite_master
                       WHERE type = 'table'
                         AND name = 'vehicles'
                       """)

        if not cursor.fetchone():
            print("❌ Таблица vehicles не найдена")
            return False

        # Получаем текущую структуру таблицы
        cursor.execute("PRAGMA table_info(vehicles)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Существующие колонки: {columns}")

        # Добавляем колонку vehicle_type если её нет
        if 'vehicle_type' not in columns:
            try:
                cursor.execute("ALTER TABLE vehicles ADD COLUMN vehicle_type TEXT")
                print("✅ Добавлена колонка: vehicle_type")
            except sqlite3.Error as e:
                print(f"⚠️ Колонка vehicle_type уже существует или ошибка: {e}")

        # Получаем все автомобили
        cursor.execute("""
                       SELECT id, make, model, driver_name, color, year, license_plate, vehicle_type, seats
                       FROM vehicles
                       """)

        vehicles = cursor.fetchall()
        print(f"📊 Найдено автомобилей: {len(vehicles)}")

        if not vehicles:
            print("ℹ️ Нет автомобилей для обновления")
            return True

        print("\n" + "=" * 60)
        print("🔄 ОБНОВЛЕНИЕ ТИПОВ АВТОМОБИЛЕЙ")
        print("=" * 60)

        updated_count = 0
        lancer_fixed = 0
        type_stats = Counter()

        for vehicle in vehicles:
            vehicle_id, make, model, driver_name, color, year, license_plate, current_type, seats = vehicle

            print(f"\n🚗 [{vehicle_id}] {make} {model} ({license_plate})")
            print(f"   Текущий тип: {current_type}")

            # Определяем новый тип
            new_type = detect_vehicle_type_migration(make or "", model or "")
            new_seats = get_seats_by_type_migration(new_type)

            # Специальная проверка для Lancer Sportback
            if model and 'lancer' in model.lower() and 'sportback' in model.lower():
                if current_type != 'HATCHBACK':
                    print(f"   🎯 ИСПРАВЛЕНИЕ: Lancer Sportback {current_type} → HATCHBACK")
                    lancer_fixed += 1

            if current_type != new_type or seats != new_seats:
                try:
                    cursor.execute("""
                                   UPDATE vehicles
                                   SET vehicle_type = ?,
                                       seats        = ?
                                   WHERE id = ?
                                   """, (new_type, new_seats, vehicle_id))

                    print(f"   ✅ Обновлено: {current_type} → {new_type}, мест: {seats} → {new_seats}")
                    updated_count += 1

                except sqlite3.Error as e:
                    print(f"   ❌ Ошибка обновления: {e}")
            else:
                print(f"   ➡️ Без изменений: {current_type}")

            type_stats[new_type] += 1

        # Подтверждаем изменения
        conn.commit()

        print("\n" + "=" * 60)
        print("📈 СТАТИСТИКА МИГРАЦИИ")
        print("=" * 60)
        print(f"✅ Обработано автомобилей: {len(vehicles)}")
        print(f"🔄 Обновлено записей: {updated_count}")
        print(f"🎯 Исправлено Lancer Sportback: {lancer_fixed}")

        print(f"\n📊 РАСПРЕДЕЛЕНИЕ ПО ТИПАМ:")
        for vehicle_type, count in sorted(type_stats.items()):
            percentage = (count / len(vehicles)) * 100
            print(f"   {vehicle_type:12} : {count:2} шт. ({percentage:.1f}%)")

        # Проверяем результат
        cursor.execute("""
                       SELECT vehicle_type, COUNT(*) as count
                       FROM vehicles
                       WHERE vehicle_type IS NOT NULL
                       GROUP BY vehicle_type
                       ORDER BY count DESC
                       """)

        print(f"\n🔍 ПРОВЕРКА РЕЗУЛЬТАТОВ:")
        results = cursor.fetchall()
        for vehicle_type, count in results:
            print(f"   {vehicle_type}: {count} автомобилей")

        # Проверяем Lancer Sportback
        cursor.execute("""
                       SELECT COUNT(*)
                       FROM vehicles
                       WHERE model LIKE '%lancer%'
                         AND model LIKE '%sportback%'
                         AND vehicle_type = 'HATCHBACK'
                       """)
        lancer_check = cursor.fetchone()[0]
        print(f"\n🎯 Lancer Sportback с типом HATCHBACK: {lancer_check}")

        print("\n" + "=" * 60)
        print("🎉 МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"💥 Ошибка миграции: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def verify_migration():
    """Проверка результатов миграции"""
    db_path = Path("data/database.db")

    if not db_path.exists():
        print("❌ База данных не найдена")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("\n🔍 ДЕТАЛЬНАЯ ПРОВЕРКА МИГРАЦИИ")
        print("=" * 60)

        # Проверяем колонку vehicle_type
        cursor.execute("PRAGMA table_info(vehicles)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'vehicle_type' not in columns:
            print("❌ Колонка vehicle_type отсутствует")
            return False
        else:
            print("✅ Колонка vehicle_type присутствует")

        # Статистика по типам
        cursor.execute("""
                       SELECT vehicle_type,
                              COUNT(*) as count,
                GROUP_CONCAT(make || ' ' || model, ', ') as examples
                       FROM vehicles
                       WHERE vehicle_type IS NOT NULL
                       GROUP BY vehicle_type
                       ORDER BY count DESC
                       """)

        results = cursor.fetchall()
        print(f"\n📊 СТАТИСТИКА ПО ТИПАМ:")
        for vehicle_type, count, examples in results:
            print(f"\n🚙 {vehicle_type} ({count} шт.):")
            examples_list = examples.split(', ')[:3]  # Показываем первые 3 примера
            for example in examples_list:
                print(f"   • {example}")
            if len(examples.split(', ')) > 3:
                print(f"   • ... и ещё {len(examples.split(', ')) - 3}")

        # Специальная проверка Lancer Sportback
        cursor.execute("""
                       SELECT make, model, vehicle_type, license_plate
                       FROM vehicles
                       WHERE model LIKE '%lancer%'
                         AND model LIKE '%sportback%'
                       """)

        lancer_results = cursor.fetchall()
        print(f"\n🎯 ПРОВЕРКА LANCER SPORTBACK:")
        if lancer_results:
            for make, model, vehicle_type, plate in lancer_results:
                status = "✅" if vehicle_type == "HATCHBACK" else "❌"
                print(f"   {status} {make} {model} ({plate}) → {vehicle_type}")
        else:
            print("   ℹ️ Lancer Sportback не найден в базе")

        # Проверяем записи без типа
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE vehicle_type IS NULL")
        null_count = cursor.fetchone()[0]

        if null_count > 0:
            print(f"\n⚠️ Найдено записей без типа: {null_count}")
            cursor.execute("""
                           SELECT make, model, license_plate
                           FROM vehicles
                           WHERE vehicle_type IS NULL LIMIT 5
                           """)
            for make, model, plate in cursor.fetchall():
                print(f"   • {make} {model} ({plate})")
        else:
            print(f"\n✅ Все записи имеют тип")

        print(f"\n🎉 Проверка завершена!")
        return True

    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    print("🚗 МИГРАЦИЯ ТИПОВ АВТОМОБИЛЕЙ")
    print("Исправляет Lancer Sportback и добавляет новые типы")
    print("=" * 60)

    # Выполняем миграцию
    if migrate_vehicle_types():
        print()
        # Проверяем результат
        verify_migration()

        print("\n" + "=" * 60)
        print("✅ ВСЁ ГОТОВО!")
        print("✅ Теперь Lancer Sportback корректно определяется как Hatchback")
        print("✅ Добавлены новые типы: WAGON, COUPE, MPV, CROSSOVER и др.")
        print("✅ Ошибки с типом WAGON исправлены")
    else:
        print("\n❌ МИГРАЦИЯ НЕ ВЫПОЛНЕНА")
        print("Проверьте ошибки выше и повторите попытку")

    print("=" * 60)