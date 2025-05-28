#!/usr/bin/env python3
"""
Скрипт очистки старых заказов с неправильными ценами
Архивирует заказы с ценой 71.50 zł и создает отчет
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path


def cleanup_old_orders():
    """Очистка старых заказов с архивированием"""

    # Пути к базам данных
    main_db = Path("data/database.db")
    archive_db = Path("data/archive_database.db")

    if not main_db.exists():
        print("❌ Основная база данных не найдена")
        return False

    # Создаем архивную базу
    archive_db.parent.mkdir(exist_ok=True)

    print("🧹 НАЧИНАЕМ ОЧИСТКУ СТАРЫХ ЗАКАЗОВ")
    print("=" * 50)

    try:
        # Подключаемся к базам
        main_conn = sqlite3.connect(main_db)
        archive_conn = sqlite3.connect(archive_db)

        # Создаем архивную таблицу
        archive_conn.execute("""
                             CREATE TABLE IF NOT EXISTS archived_orders
                             (
                                 id
                                 INTEGER
                                 PRIMARY
                                 KEY,
                                 original_id
                                 INTEGER,
                                 order_data
                                 TEXT,
                                 reason
                                 TEXT,
                                 archived_at
                                 TIMESTAMP
                                 DEFAULT
                                 CURRENT_TIMESTAMP
                             )
                             """)

        # Находим проблемные заказы алкоголя
        cursor = main_conn.execute("""
                                   SELECT id, estimated_price, price, order_type, products, created_at, status
                                   FROM rides
                                   WHERE (order_type = 'alcohol_delivery' OR notes LIKE '%ALCOHOL DELIVERY%')
                                     AND (estimated_price = 71.50 OR price = 71.50)
                                   """)

        problem_orders = cursor.fetchall()

        if not problem_orders:
            print("✅ Проблемных заказов не найдено")
            return True

        print(f"🔍 Найдено проблемных заказов: {len(problem_orders)}")
        print()

        archived_count = 0

        for order in problem_orders:
            order_id, est_price, price, order_type, products, created_at, status = order

            print(f"📦 Заказ #{order_id}:")
            print(f"   Цена: {est_price} / {price} zł")
            print(f"   Продукты: {products[:50] if products else 'N/A'}...")
            print(f"   Статус: {status}")
            print(f"   Дата: {created_at}")

            # Определяем действие
            action = "UNKNOWN"  # Инициализируем переменную

            if status in ['pending', 'cancelled']:
                # Удаляем неактивные заказы
                action = "DELETE"
                reason = f"Inactive order with wrong price {est_price or price} zł"

                # Архивируем
                order_data = {
                    'id': order_id,
                    'estimated_price': est_price,
                    'price': price,
                    'order_type': order_type,
                    'products': products,
                    'created_at': created_at,
                    'status': status
                }

                archive_conn.execute(
                    "INSERT INTO archived_orders (original_id, order_data, reason) VALUES (?, ?, ?)",
                    (order_id, json.dumps(order_data), reason)
                )

                # Удаляем из основной базы
                main_conn.execute("DELETE FROM rides WHERE id = ?", (order_id,))
                archived_count += 1

            elif status in ['accepted', 'in_progress', 'completed']:
                # Активные заказы - исправляем цену
                action = "FIX_PRICE"
                reason = f"Fixed price from {est_price or price} zł to 20 zł"

                # Исправляем цену на правильную
                main_conn.execute(
                    "UPDATE rides SET estimated_price = 20.0, price = 20.0 WHERE id = ?",
                    (order_id,)
                )

                # Записываем в лог архива
                log_data = {
                    'id': order_id,
                    'old_price': est_price or price,
                    'new_price': 20.0,
                    'status': status
                }

                archive_conn.execute(
                    "INSERT INTO archived_orders (original_id, order_data, reason) VALUES (?, ?, ?)",
                    (order_id, json.dumps(log_data), reason)
                )
            else:
                # Неизвестный статус - исправляем цену но не удаляем
                action = "FIX_UNKNOWN_STATUS"
                reason = f"Fixed price for unknown status {status}"

                main_conn.execute(
                    "UPDATE rides SET estimated_price = 20.0, price = 20.0 WHERE id = ?",
                    (order_id,)
                )

            print(f"   ✅ Действие: {action}")
            print()

        # Подтверждаем изменения
        main_conn.commit()
        archive_conn.commit()

        print("=" * 50)
        print("📊 ИТОГИ ОЧИСТКИ:")
        print(f"✅ Обработано заказов: {len(problem_orders)}")
        print(f"🗑️ Удалено неактивных: {archived_count}")
        print(f"🔧 Исправлено активных: {len(problem_orders) - archived_count}")

        # Проверяем результат
        cursor = main_conn.execute("""
                                   SELECT COUNT(*)
                                   FROM rides
                                   WHERE (order_type = 'alcohol_delivery' OR notes LIKE '%ALCOHOL DELIVERY%')
                                     AND (estimated_price = 71.50 OR price = 71.50)
                                   """)

        remaining = cursor.fetchone()[0]

        if remaining == 0:
            print("🎉 ВСЕ ПРОБЛЕМНЫЕ ЗАКАЗЫ ОЧИЩЕНЫ!")
        else:
            print(f"⚠️ Осталось проблемных заказов: {remaining}")

        # Создаем отчет
        create_cleanup_report(archive_conn)

        return True

    except Exception as e:
        print(f"💥 Ошибка очистки: {e}")
        return False

    finally:
        main_conn.close()
        archive_conn.close()


def create_cleanup_report(archive_conn):
    """Создает отчет по очистке"""

    try:
        cursor = archive_conn.execute("""
                                      SELECT reason, COUNT(*) as count
                                      FROM archived_orders
                                      GROUP BY reason
                                      """)

        report_data = cursor.fetchall()

        report_text = f"""
📊 ОТЧЕТ ПО ОЧИСТКЕ ЗАКАЗОВ
Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 50}

СТАТИСТИКА ДЕЙСТВИЙ:
"""

        for reason, count in report_data:
            report_text += f"• {reason}: {count} заказов\n"

        report_text += f"""
{'=' * 50}
✅ Очистка завершена успешно
📁 Архив сохранен в: data/archive_database.db
"""

        # Сохраняем отчет в файл
        report_file = Path("data/cleanup_report.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_text)

        print(f"📄 Отчет сохранен: {report_file}")
        print(report_text)

    except Exception as e:
        print(f"❌ Ошибка создания отчета: {e}")


def verify_cleanup():
    """Проверяет результаты очистки"""

    main_db = Path("data/database.db")

    if not main_db.exists():
        print("❌ База данных не найдена")
        return

    conn = sqlite3.connect(main_db)

    try:
        # Проверяем заказы алкоголя
        cursor = conn.execute("""
                              SELECT COUNT(*)                                                             as total,
                                     COUNT(CASE WHEN estimated_price = 20.0 OR price = 20.0 THEN 1 END)   as correct_price,
                                     COUNT(CASE WHEN estimated_price = 71.50 OR price = 71.50 THEN 1 END) as wrong_price
                              FROM rides
                              WHERE order_type = 'alcohol_delivery'
                                 OR notes LIKE '%ALCOHOL DELIVERY%'
                              """)

        total, correct, wrong = cursor.fetchone()

        print("🔍 ПРОВЕРКА РЕЗУЛЬТАТОВ:")
        print(f"📊 Всего заказов алкоголя: {total}")
        print(f"✅ С правильной ценой (20 zł): {correct}")
        print(f"❌ С неправильной ценой (71.50 zł): {wrong}")

        if wrong == 0:
            print("🎉 ВСЕ ЦЕНЫ ИСПРАВЛЕНЫ!")
        else:
            print("⚠️ Есть заказы с неправильными ценами")

        # Общая статистика
        cursor = conn.execute("SELECT COUNT(*) FROM rides")
        total_orders = cursor.fetchone()[0]

        cursor = conn.execute("""
                              SELECT order_type, COUNT(*)
                              FROM rides
                              GROUP BY order_type
                              """)

        types = cursor.fetchall()

        print(f"\n📈 ОБЩАЯ СТАТИСТИКА:")
        print(f"📦 Всего заказов в системе: {total_orders}")
        for order_type, count in types:
            print(f"   • {order_type or 'обычные'}: {count}")

    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")

    finally:
        conn.close()


if __name__ == "__main__":
    print("🧹 УТИЛИТА ОЧИСТКИ СТАРЫХ ЗАКАЗОВ")
    print("=" * 50)

    choice = input(
        "Выберите действие:\n1. Очистить заказы\n2. Проверить результаты\n3. Оба действия\nВаш выбор (1-3): ")

    if choice in ['1', '3']:
        if cleanup_old_orders():
            print("\n✅ Очистка завершена успешно!")
        else:
            print("\n❌ Очистка завершилась с ошибками")

    if choice in ['2', '3']:
        print("\n" + "=" * 50)
        verify_cleanup()

    print("\n🎉 Готово!")