"""
Улучшенная система логирования для такси-ботов
Отслеживание всех операций и ошибок
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
import sqlite3


class TaxiLogger:
    """Специализированный логгер для такси-системы"""

    def __init__(self, bot_name: str = "taxi_bot"):
        self.bot_name = bot_name
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Создаем основной логгер
        self.logger = logging.getLogger(f"taxi_{bot_name}")
        self.logger.setLevel(logging.INFO)

        # Очищаем старые хендлеры
        self.logger.handlers.clear()

        # Настраиваем хендлеры
        self._setup_handlers()

        # База для системных логов
        self._setup_db_logging()

    def _setup_handlers(self):
        """Настройка обработчиков логов"""

        # Формат логов
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 1. Консольный вывод
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 2. Основной файл (с ротацией)
        main_file = self.logs_dir / f"{self.bot_name}.log"
        file_handler = RotatingFileHandler(
            main_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # 3. Файл ошибок
        error_file = self.logs_dir / f"{self.bot_name}_errors.log"
        error_handler = RotatingFileHandler(
            error_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)

        # 4. JSON файл для системных событий
        json_file = self.logs_dir / f"{self.bot_name}_events.jsonl"
        self.json_handler = JsonFileHandler(json_file)

    def _setup_db_logging(self):
        """Настройка логирования в базу данных"""
        db_path = Path("data/system_logs.db")
        db_path.parent.mkdir(exist_ok=True)

        conn = sqlite3.connect(db_path)
        conn.execute("""
                     CREATE TABLE IF NOT EXISTS system_logs
                     (
                         id
                         INTEGER
                         PRIMARY
                         KEY
                         AUTOINCREMENT,
                         timestamp
                         DATETIME
                         DEFAULT
                         CURRENT_TIMESTAMP,
                         bot_name
                         TEXT,
                         level
                         TEXT,
                         event_type
                         TEXT,
                         message
                         TEXT,
                         data
                         TEXT,
                         user_id
                         INTEGER,
                         order_id
                         INTEGER
                     )
                     """)
        conn.close()

        self.db_path = db_path

    def info(self, message: str, **kwargs):
        """Информационное сообщение"""
        self.logger.info(message)
        self._log_to_json('INFO', 'info', message, kwargs)

    def error(self, message: str, **kwargs):
        """Сообщение об ошибке"""
        self.logger.error(message)
        self._log_to_json('ERROR', 'error', message, kwargs)

    def warning(self, message: str, **kwargs):
        """Предупреждение"""
        self.logger.warning(message)
        self._log_to_json('WARNING', 'warning', message, kwargs)

    def order_created(self, order_id: int, user_id: int, order_data: dict):
        """Лог создания заказа"""
        message = f"Order {order_id} created by user {user_id}"
        self.logger.info(message)
        self._log_to_db('INFO', 'order_created', message, order_data, user_id, order_id)

    def order_accepted(self, order_id: int, driver_id: int):
        """Лог принятия заказа"""
        message = f"Order {order_id} accepted by driver {driver_id}"
        self.logger.info(message)
        self._log_to_db('INFO', 'order_accepted', message, {'driver_id': driver_id}, driver_id, order_id)

    def order_completed(self, order_id: int, driver_id: int, final_price: float):
        """Лог завершения заказа"""
        message = f"Order {order_id} completed by driver {driver_id}, price: {final_price} zł"
        self.logger.info(message)
        self._log_to_db('INFO', 'order_completed', message, {'final_price': final_price}, driver_id, order_id)

    def system_error(self, error: Exception, context: dict = None):
        """Лог системной ошибки"""
        message = f"System error: {str(error)}"
        self.logger.error(message, exc_info=True)

        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        self._log_to_db('ERROR', 'system_error', message, error_data)

    def user_action(self, user_id: int, action: str, details: dict = None):
        """Лог действий пользователя"""
        message = f"User {user_id} performed action: {action}"
        self.logger.info(message)
        self._log_to_db('INFO', 'user_action', message, details or {}, user_id)

    def _log_to_json(self, level: str, event_type: str, message: str, data: dict):
        """Запись в JSON файл"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'bot_name': self.bot_name,
                'level': level,
                'event_type': event_type,
                'message': message,
                'data': data
            }
            self.json_handler.emit(log_entry)
        except Exception as e:
            self.logger.error(f"Failed to write JSON log: {e}")

    def _log_to_db(self, level: str, event_type: str, message: str, data: dict = None, user_id: int = None,
                   order_id: int = None):
        """Запись в базу данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                         INSERT INTO system_logs
                             (bot_name, level, event_type, message, data, user_id, order_id)
                         VALUES (?, ?, ?, ?, ?, ?, ?)
                         """, (
                             self.bot_name,
                             level,
                             event_type,
                             message,
                             json.dumps(data) if data else None,
                             user_id,
                             order_id
                         ))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Failed to write DB log: {e}")


class JsonFileHandler:
    """Обработчик для записи в JSON Lines файл"""

    def __init__(self, filename: Path):
        self.filename = filename

    def emit(self, record: dict):
        """Записать запись в файл"""
        try:
            with open(self.filename, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        except Exception:
            pass  # Игнорируем ошибки записи JSON


# Глобальные экземпляры логгеров
client_logger = TaxiLogger("client_bot")
driver_logger = TaxiLogger("driver_bot")
system_logger = TaxiLogger("system")


# Утилиты для анализа логов
def analyze_logs(days: int = 7):
    """Анализ логов за последние N дней"""

    db_path = Path("data/system_logs.db")
    if not db_path.exists():
        print("❌ База логов не найдена")
        return

    conn = sqlite3.connect(db_path)

    try:
        # Статистика по событиям
        cursor = conn.execute("""
            SELECT event_type, level, COUNT(*) as count
            FROM system_logs
            WHERE timestamp > datetime('now', '-{} days')
            GROUP BY event_type, level
            ORDER BY count DESC
        """.format(days))

        events = cursor.fetchall()

        print(f"📊 АНАЛИЗ ЛОГОВ ЗА ПОСЛЕДНИЕ {days} ДНЕЙ")
        print("=" * 50)
        print("📈 События по типам:")

        for event_type, level, count in events:
            emoji = "✅" if level == "INFO" else "⚠️" if level == "WARNING" else "❌"
            print(f"{emoji} {event_type} ({level}): {count}")

        # Статистика по заказам
        cursor = conn.execute("""
            SELECT 
                COUNT(CASE WHEN event_type = 'order_created' THEN 1 END) as created,
                COUNT(CASE WHEN event_type = 'order_accepted' THEN 1 END) as accepted,
                COUNT(CASE WHEN event_type = 'order_completed' THEN 1 END) as completed
            FROM system_logs
            WHERE timestamp > datetime('now', '-{} days')
        """.format(days))

        created, accepted, completed = cursor.fetchone()

        print(f"\n🚖 Статистика заказов:")
        print(f"📦 Создано: {created}")
        print(f"✅ Принято: {accepted}")
        print(f"🏁 Завершено: {completed}")

        if created > 0:
            acceptance_rate = (accepted / created) * 100
            completion_rate = (completed / accepted) * 100 if accepted > 0 else 0
            print(f"📊 Процент принятия: {acceptance_rate:.1f}%")
            print(f"📊 Процент завершения: {completion_rate:.1f}%")

        # Топ пользователей
        cursor = conn.execute("""
            SELECT user_id, COUNT(*) as actions
            FROM system_logs
            WHERE user_id IS NOT NULL 
            AND timestamp > datetime('now', '-{} days')
            GROUP BY user_id
            ORDER BY actions DESC
            LIMIT 5
        """.format(days))

        top_users = cursor.fetchall()

        if top_users:
            print(f"\n👥 Топ активных пользователей:")
            for user_id, actions in top_users:
                print(f"   User {user_id}: {actions} действий")

        # Ошибки
        cursor = conn.execute("""
            SELECT message, COUNT(*) as count
            FROM system_logs
            WHERE level = 'ERROR'
            AND timestamp > datetime('now', '-{} days')
            GROUP BY message
            ORDER BY count DESC
            LIMIT 5
        """.format(days))

        errors = cursor.fetchall()

        if errors:
            print(f"\n❌ Частые ошибки:")
            for message, count in errors:
                print(f"   {message[:60]}...: {count} раз")

    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")

    finally:
        conn.close()


def cleanup_old_logs(days: int = 30):
    """Очистка старых логов"""

    db_path = Path("data/system_logs.db")
    if not db_path.exists():
        return

    conn = sqlite3.connect(db_path)

    try:
        # Подсчитываем записи для удаления
        cursor = conn.execute("""
            SELECT COUNT(*) FROM system_logs
            WHERE timestamp < datetime('now', '-{} days')
        """.format(days))

        old_count = cursor.fetchone()[0]

        if old_count > 0:
            # Удаляем старые записи
            conn.execute("""
                DELETE FROM system_logs
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days))

            conn.commit()
            print(f"🗑️ Удалено старых записей логов: {old_count}")
        else:
            print("✅ Старых логов для удаления не найдено")

    except Exception as e:
        print(f"❌ Ошибка очистки логов: {e}")

    finally:
        conn.close()


# Команды для CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "analyze":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            analyze_logs(days)

        elif command == "cleanup":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            cleanup_old_logs(days)

        else:
            print("❌ Неизвестная команда")
            print("Доступные команды:")
            print("  python logging_system.py analyze [days]")
            print("  python logging_system.py cleanup [days]")
    else:
        print("📊 Система логирования такси-ботов")
        print("Для анализа: python logging_system.py analyze")
        print("Для очистки: python logging_system.py cleanup")