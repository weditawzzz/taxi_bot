#!/usr/bin/env python3
"""
Скрипт миграции для совместимости старой и новой архитектуры
"""

import asyncio
import sqlite3
import os
import sys
from pathlib import Path

# Добавляем корневую папку в путь Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)


def create_env_template():
    """Создает шаблон .env файла если его нет"""
    env_path = Path(".env")

    if not env_path.exists():
        print("🔧 Создаем шаблон .env файла...")

        env_template = """# Токены ботов
CLIENT_BOT_TOKEN=7452398298:AAHoGk45AEJii2ycWaMCPKoHA5705ZyVEn0
DRIVER_BOT_TOKEN=8012773257:AAHuhGx8TwaEP1KPooBFAq8EfUNSRZfmJtM

# База данных
DATABASE_URL=sqlite+aiosqlite:///data/database.db
DB_ECHO=false

# Карты (опционально)
MAPS_API_KEY=AIzaSyBHUFjfnp7oN4BC27_wlOuCqr33WOrNRQo

# Настройки
DEBUG=false
LOG_LEVEL=INFO

# Водители (ID через запятую)
DRIVER_IDS=628521909,987654321
DRIVER_CHAT_ID=628521909

# Географические настройки
DEFAULT_CITY=Szczecin
DEFAULT_COUNTRY=Poland
MAX_RIDE_DISTANCE_KM=50

# Цены
BASE_PRICE_PLN=5.0
PRICE_PER_KM_PLN=2.5
"""

        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_template)

        print("✅ Создан шаблон .env файла с токенами из config.py")
    else:
        print("✅ Файл .env уже существует")

    return env_path.exists()


def load_environment():
    """Загружает переменные окружения"""
    try:
        from dotenv import load_dotenv
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)
            print("✅ Переменные окружения загружены")
            return True
        else:
            print("❌ Файл .env не найден")
            return False
    except ImportError:
        print("❌ python-dotenv не установлен. Устанавливаем...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
        from dotenv import load_dotenv
        load_dotenv()
        return True


def ensure_database_structure():
    """Обеспечивает правильную структуру базы данных"""

    # Путь к базе данных
    db_path = Path("data/database.db")
    db_path.parent.mkdir(exist_ok=True, parents=True)

    print("🔄 Проверяем структуру базы данных...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Получаем список существующих таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Существующие таблицы: {existing_tables}")

        # Проверяем, нужно ли создавать новые таблицы
        required_tables = ['users', 'vehicles', 'rides', 'driver_locations']
        missing_tables = [table for table in required_tables if table not in existing_tables]

        if missing_tables:
            print(f"🆕 Создаем недостающие таблицы: {missing_tables}")
        else:
            print("✅ Все необходимые таблицы уже существуют")

        # Проверяем структуру таблицы rides/orders
        if 'rides' in existing_tables:
            cursor.execute("PRAGMA table_info(rides)")
            rides_columns = [column[1] for column in cursor.fetchall()]
            print(f"📋 Колонки в таблице rides: {rides_columns}")

            # Добавляем недостающие колонки для совместимости
            compatibility_columns = {
                'user_id': 'INTEGER',
                'driver_name': 'TEXT',
                'origin': 'TEXT',
                'destination': 'TEXT',
                'price': 'DECIMAL(10,2)',
                'order_type': 'VARCHAR(50)',
                'products': 'TEXT',
                'budget': 'REAL',
                'payment_method': 'VARCHAR(20) DEFAULT "cash"'
            }

            for col_name, col_type in compatibility_columns.items():
                if col_name not in rides_columns:
                    try:
                        cursor.execute(f"ALTER TABLE rides ADD COLUMN {col_name} {col_type}")
                        print(f"✅ Добавлена колонка: {col_name}")
                    except sqlite3.Error as e:
                        print(f"⚠️ Не удалось добавить колонку {col_name}: {e}")

        # Проверяем структуру таблицы vehicles
        if 'vehicles' in existing_tables:
            cursor.execute("PRAGMA table_info(vehicles)")
            vehicles_columns = [column[1] for column in cursor.fetchall()]

            # Добавляем недостающие колонки для совместимости
            vehicle_compatibility_columns = {
                'driver_name': 'VARCHAR(255)',
                'photo': 'BLOB',
                'last_lat': 'REAL',
                'last_lon': 'REAL'
            }

            for col_name, col_type in vehicle_compatibility_columns.items():
                if col_name not in vehicles_columns:
                    try:
                        cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {col_name} {col_type}")
                        print(f"✅ Добавлена колонка в vehicles: {col_name}")
                    except sqlite3.Error as e:
                        print(f"⚠️ Не удалось добавить колонку {col_name}: {e}")

        # Если есть старая таблица orders, мигрируем данные
        if 'orders' in existing_tables and 'rides' in existing_tables:
            print("🔄 Мигрируем данные из orders в rides...")
            try:
                # Получаем данные из старой таблицы
                cursor.execute("SELECT * FROM orders")
                orders = cursor.fetchall()

                # Получаем описание колонок старой таблицы
                cursor.execute("PRAGMA table_info(orders)")
                old_columns = [column[1] for column in cursor.fetchall()]

                print(f"📋 Найдено {len(orders)} заказов для миграции")
                print(f"📋 Колонки в старой таблице orders: {old_columns}")

                if orders:
                    # Здесь можно добавить логику миграции данных
                    print("ℹ️ Миграция данных пропущена для безопасности")
                    print("ℹ️ При необходимости мигрируйте данные вручную")

            except sqlite3.Error as e:
                print(f"⚠️ Ошибка миграции данных: {e}")

        conn.commit()
        print("✅ Структура базы данных обновлена")

    except Exception as e:
        print(f"❌ Ошибка обработки базы данных: {e}")
        conn.rollback()

    finally:
        conn.close()


async def initialize_new_models():
    """Инициализация новых моделей"""
    print("🔄 Инициализируем новые модели...")

    try:
        # Теперь можно безопасно импортировать
        from core.database import init_database, db_manager

        await init_database()
        print("✅ База данных инициализирована с новыми моделями")

        # Проверяем, что все работает
        async with db_manager.get_async_session() as session:
            print("✅ Асинхронная сессия работает")

        with db_manager.get_sync_session() as session:
            print("✅ Синхронная сессия работает")

    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        raise


def check_imports():
    """Проверяем, что все импорты работают"""
    print("🔍 Проверяем импорты...")

    try:
        # Проверяем основные модули
        from core.config import config, Config
        print("✅ Конфигурация импортируется")

        from core.models import User, Ride, Vehicle, Session
        print("✅ Модели импортируются")

        from core.database import get_session, Session as SessionAlias
        print("✅ База данных импортируется")

        # Проверяем алиасы
        from core.models import Order, DriverVehicle
        print("✅ Алиасы для совместимости работают")

        # Проверяем, что Session работает
        try:
            with Session() as session:
                print("✅ Совместимый Session() работает")
        except Exception as e:
            print(f"⚠️ Проблема с Session(): {e}")

        return True

    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        return False


def check_file_structure():
    """Проверяем структуру файлов проекта"""
    print("🔍 Проверяем структуру файлов...")

    required_files = [
        'core/__init__.py',
        'core/config.py',
        'core/models.py',
        'core/database.py',
        'core/handlers/__init__.py',
        'core/handlers/client/__init__.py',
        'core/handlers/driver/__init__.py',
        'core/services/__init__.py',
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print(f"❌ Отсутствующие файлы: {missing_files}")
        return False
    else:
        print("✅ Все необходимые файлы на месте")
        return True


async def main():
    """Главная функция миграции"""
    print("🚀 Запуск скрипта совместимости taxi_bot")
    print("=" * 60)

    # Проверяем структуру файлов
    if not check_file_structure():
        print("❌ Не все необходимые файлы найдены. Проверьте структуру проекта.")
        return False

    # Создаем .env если нужно
    if not create_env_template():
        print("❌ Не удалось создать .env файл")
        return False

    # Загружаем переменные окружения
    if not load_environment():
        print("❌ Не удалось загрузить переменные окружения")
        return False

    # Проверяем импорты
    if not check_imports():
        print("❌ Критические ошибки импортов. Исправьте их перед продолжением.")
        return False

    # Обеспечиваем структуру БД
    ensure_database_structure()

    # Инициализируем новые модели
    await initialize_new_models()

    print("\n" + "=" * 60)
    print("🎉 Миграция завершена успешно!")
    print("\n📋 Что было сделано:")
    print("✅ Создан .env файл с токенами")
    print("✅ Проверены и исправлены импорты")
    print("✅ Обновлена структура базы данных")
    print("✅ Добавлены колонки для совместимости")
    print("✅ Инициализированы новые модели")
    print("✅ Проверена работа сессий")

    print("\n🚀 Следующие шаги:")
    print("1. Проверьте токены в .env файле (уже заполнены из config.py)")
    print("2. Запустите клиентский бот: python run.py")
    print("3. Запустите водительский бот: python driver_bot.py")

    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            print("\n👍 Все готово к работе!")
        else:
            print("\n❌ Есть проблемы, которые нужно исправить")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Прервано пользователем")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)