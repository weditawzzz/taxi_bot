"""
Система мониторинга производительности такси-ботов
Отслеживает метрики, производительность и здоровье системы
"""

import asyncio
import time
import psutil
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional
import threading
from contextlib import asynccontextmanager


@dataclass
class SystemMetrics:
    """Метрики системы"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    active_connections: int
    response_time_ms: float
    orders_per_minute: int
    error_rate: float


@dataclass
class BotMetrics:
    """Метрики бота"""
    bot_name: str
    uptime_seconds: int
    messages_sent: int
    messages_received: int
    errors_count: int
    average_response_time: float
    active_users: int
    memory_mb: float


class PerformanceMonitor:
    """Монитор производительности системы"""

    def __init__(self):
        self.monitoring_db = Path("data/monitoring.db")
        self.monitoring_db.parent.mkdir(exist_ok=True)

        self._init_database()
        self._start_time = time.time()
        self._metrics_cache = {}
        self._bot_metrics = {}

        # Счетчики
        self.counters = {
            'orders_created': 0,
            'orders_completed': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
            'api_calls': 0
        }

        # Времена ответов
        self.response_times = []
        self.max_response_times = 1000  # Хранить последние 1000 измерений

    def _init_database(self):
        """Инициализация базы мониторинга"""

        conn = sqlite3.connect(self.monitoring_db)

        # Таблица системных метрик
        conn.execute("""
                     CREATE TABLE IF NOT EXISTS system_metrics
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
                         cpu_percent
                         REAL,
                         memory_percent
                         REAL,
                         memory_used_mb
                         REAL,
                         disk_usage_percent
                         REAL,
                         active_connections
                         INTEGER,
                         response_time_ms
                         REAL,
                         orders_per_minute
                         INTEGER,
                         error_rate
                         REAL
                     )
                     """)

        # Таблица метрик ботов
        conn.execute("""
                     CREATE TABLE IF NOT EXISTS bot_metrics
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
                         uptime_seconds
                         INTEGER,
                         messages_sent
                         INTEGER,
                         messages_received
                         INTEGER,
                         errors_count
                         INTEGER,
                         average_response_time
                         REAL,
                         active_users
                         INTEGER,
                         memory_mb
                         REAL
                     )
                     """)

        # Таблица алертов
        conn.execute("""
                     CREATE TABLE IF NOT EXISTS alerts
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
                         alert_type
                         TEXT,
                         severity
                         TEXT,
                         message
                         TEXT,
                         metric_value
                         REAL,
                         threshold
                         REAL,
                         resolved
                         BOOLEAN
                         DEFAULT
                         FALSE
                     )
                     """)

        conn.commit()
        conn.close()

    def collect_system_metrics(self) -> SystemMetrics:
        """Собирает метрики системы"""

        # CPU и память
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)

        # Диск
        disk = psutil.disk_usage('/')
        disk_usage_percent = (disk.used / disk.total) * 100

        # Сетевые соединения
        try:
            connections = len(psutil.net_connections())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            connections = 0

        # Среднее время ответа
        avg_response_time = 0
        if self.response_times:
            avg_response_time = sum(self.response_times) / len(self.response_times)

        # Заказы в минуту
        orders_per_minute = self._calculate_orders_per_minute()

        # Частота ошибок
        error_rate = self._calculate_error_rate()

        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            disk_usage_percent=disk_usage_percent,
            active_connections=connections,
            response_time_ms=avg_response_time,
            orders_per_minute=orders_per_minute,
            error_rate=error_rate
        )

    def _calculate_orders_per_minute(self) -> int:
        """Вычисляет количество заказов в минуту"""
        try:
            conn = sqlite3.connect("data/database.db")
            cursor = conn.execute("""
                                  SELECT COUNT(*)
                                  FROM rides
                                  WHERE created_at > datetime('now', '-1 minute')
                                  """)
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def _calculate_error_rate(self) -> float:
        """Вычисляет частоту ошибок"""
        try:
            conn = sqlite3.connect("data/system_logs.db")

            # Ошибки за последние 5 минут
            cursor = conn.execute("""
                                  SELECT COUNT(*)
                                  FROM system_logs
                                  WHERE level = 'ERROR'
                                    AND timestamp
                                      > datetime('now'
                                      , '-5 minutes')
                                  """)
            errors = cursor.fetchone()[0]

            # Всего событий за последние 5 минут
            cursor = conn.execute("""
                                  SELECT COUNT(*)
                                  FROM system_logs
                                  WHERE timestamp > datetime('now', '-5 minutes')
                                  """)
            total = cursor.fetchone()[0]

            conn.close()

            return (errors / total * 100) if total > 0 else 0

        except Exception:
            return 0

    def record_response_time(self, response_time_ms: float):
        """Записывает время ответа"""
        self.response_times.append(response_time_ms)

        # Ограничиваем размер списка
        if len(self.response_times) > self.max_response_times:
            self.response_times = self.response_times[-self.max_response_times:]

    def record_bot_metrics(self, bot_name: str, metrics: Dict):
        """Записывает метрики бота"""

        bot_metrics = BotMetrics(
            bot_name=bot_name,
            uptime_seconds=int(time.time() - self._start_time),
            messages_sent=metrics.get('messages_sent', 0),
            messages_received=metrics.get('messages_received', 0),
            errors_count=metrics.get('errors', 0),
            average_response_time=metrics.get('avg_response_time', 0),
            active_users=metrics.get('active_users', 0),
            memory_mb=metrics.get('memory_mb', 0)
        )

        self._bot_metrics[bot_name] = bot_metrics

    def save_metrics(self):
        """Сохраняет метрики в базу данных"""

        # Собираем системные метрики
        system_metrics = self.collect_system_metrics()

        conn = sqlite3.connect(self.monitoring_db)

        try:
            # Сохраняем системные метрики
            conn.execute("""
                         INSERT INTO system_metrics
                         (cpu_percent, memory_percent, memory_used_mb, disk_usage_percent,
                          active_connections, response_time_ms, orders_per_minute, error_rate)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                         """, (
                             system_metrics.cpu_percent,
                             system_metrics.memory_percent,
                             system_metrics.memory_used_mb,
                             system_metrics.disk_usage_percent,
                             system_metrics.active_connections,
                             system_metrics.response_time_ms,
                             system_metrics.orders_per_minute,
                             system_metrics.error_rate
                         ))

            # Сохраняем метрики ботов
            for bot_name, bot_metrics in self._bot_metrics.items():
                conn.execute("""
                             INSERT INTO bot_metrics
                             (bot_name, uptime_seconds, messages_sent, messages_received,
                              errors_count, average_response_time, active_users, memory_mb)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                             """, (
                                 bot_metrics.bot_name,
                                 bot_metrics.uptime_seconds,
                                 bot_metrics.messages_sent,
                                 bot_metrics.messages_received,
                                 bot_metrics.errors_count,
                                 bot_metrics.average_response_time,
                                 bot_metrics.active_users,
                                 bot_metrics.memory_mb
                             ))

            conn.commit()

        except Exception as e:
            print(f"❌ Ошибка сохранения метрик: {e}")
        finally:
            conn.close()

    def check_alerts(self):
        """Проверяет пороговые значения и создает алерты"""

        system_metrics = self.collect_system_metrics()
        alerts = []

        # Проверки системных метрик
        if system_metrics.cpu_percent > 80:
            alerts.append({
                'type': 'high_cpu',
                'severity': 'warning' if system_metrics.cpu_percent < 90 else 'critical',
                'message': f'Высокая загрузка CPU: {system_metrics.cpu_percent:.1f}%',
                'value': system_metrics.cpu_percent,
                'threshold': 80
            })

        if system_metrics.memory_percent > 85:
            alerts.append({
                'type': 'high_memory',
                'severity': 'warning' if system_metrics.memory_percent < 95 else 'critical',
                'message': f'Высокое использование памяти: {system_metrics.memory_percent:.1f}%',
                'value': system_metrics.memory_percent,
                'threshold': 85
            })

        if system_metrics.disk_usage_percent > 90:
            alerts.append({
                'type': 'high_disk',
                'severity': 'critical',
                'message': f'Мало места на диске: {system_metrics.disk_usage_percent:.1f}%',
                'value': system_metrics.disk_usage_percent,
                'threshold': 90
            })

        if system_metrics.response_time_ms > 5000:
            alerts.append({
                'type': 'slow_response',
                'severity': 'warning',
                'message': f'Медленный отклик: {system_metrics.response_time_ms:.0f}ms',
                'value': system_metrics.response_time_ms,
                'threshold': 5000
            })

        if system_metrics.error_rate > 10:
            alerts.append({
                'type': 'high_error_rate',
                'severity': 'critical',
                'message': f'Высокая частота ошибок: {system_metrics.error_rate:.1f}%',
                'value': system_metrics.error_rate,
                'threshold': 10
            })

        # Сохраняем алерты
        if alerts:
            conn = sqlite3.connect(self.monitoring_db)
            for alert in alerts:
                conn.execute("""
                             INSERT INTO alerts
                                 (alert_type, severity, message, metric_value, threshold)
                             VALUES (?, ?, ?, ?, ?)
                             """, (
                                 alert['type'],
                                 alert['severity'],
                                 alert['message'],
                                 alert['value'],
                                 alert['threshold']
                             ))
            conn.commit()
            conn.close()

            # Выводим алерты
            for alert in alerts:
                emoji = "🚨" if alert['severity'] == 'critical' else "⚠️"
                print(f"{emoji} ALERT: {alert['message']}")

    def get_dashboard_data(self, hours: int = 24) -> Dict:
        """Получает данные для дашборда"""

        conn = sqlite3.connect(self.monitoring_db)

        try:
            # Системные метрики за последние N часов
            cursor = conn.execute("""
                SELECT * FROM system_metrics 
                WHERE timestamp > datetime('now', '-{} hours')
                ORDER BY timestamp DESC
            """.format(hours))

            system_data = cursor.fetchall()

            # Метрики ботов
            cursor = conn.execute("""
                SELECT * FROM bot_metrics 
                WHERE timestamp > datetime('now', '-{} hours')
                ORDER BY timestamp DESC
            """.format(hours))

            bot_data = cursor.fetchall()

            # Активные алерты
            cursor = conn.execute("""
                                  SELECT *
                                  FROM alerts
                                  WHERE resolved = FALSE
                                    AND timestamp
                                      > datetime('now'
                                      , '-24 hours')
                                  ORDER BY timestamp DESC
                                  """)

            active_alerts = cursor.fetchall()

            # Статистика
            cursor = conn.execute("""
                SELECT 
                    AVG(cpu_percent) as avg_cpu,
                    AVG(memory_percent) as avg_memory,
                    AVG(response_time_ms) as avg_response_time,
                    MAX(orders_per_minute) as peak_orders
                FROM system_metrics 
                WHERE timestamp > datetime('now', '-{} hours')
            """.format(hours))

            stats = cursor.fetchone()

            return {
                'system_metrics': system_data,
                'bot_metrics': bot_data,
                'active_alerts': active_alerts,
                'statistics': {
                    'avg_cpu': stats[0] if stats[0] else 0,
                    'avg_memory': stats[1] if stats[1] else 0,
                    'avg_response_time': stats[2] if stats[2] else 0,
                    'peak_orders': stats[3] if stats[3] else 0
                },
                'uptime_seconds': int(time.time() - self._start_time)
            }

        except Exception as e:
            print(f"❌ Ошибка получения данных дашборда: {e}")
            return {}
        finally:
            conn.close()

    def print_dashboard(self):
        """Выводит дашборд в консоль"""

        dashboard_data = self.get_dashboard_data(1)  # За последний час

        print("\n" + "=" * 60)
        print("📊 ДАШБОРД МОНИТОРИНГА ТАКСИ-БОТОВ")
        print("=" * 60)

        # Время работы
        uptime = dashboard_data.get('uptime_seconds', 0)
        uptime_str = str(timedelta(seconds=uptime))
        print(f"⏱️  Время работы: {uptime_str}")

        # Текущие метрики
        current_metrics = self.collect_system_metrics()
        print(f"💻 CPU: {current_metrics.cpu_percent:.1f}%")
        print(f"🧠 Память: {current_metrics.memory_percent:.1f}% ({current_metrics.memory_used_mb:.0f} MB)")
        print(f"💾 Диск: {current_metrics.disk_usage_percent:.1f}%")
        print(f"🌐 Соединения: {current_metrics.active_connections}")
        print(f"⚡ Отклик: {current_metrics.response_time_ms:.0f}ms")
        print(f"📦 Заказов/мин: {current_metrics.orders_per_minute}")
        print(f"❌ Ошибки: {current_metrics.error_rate:.1f}%")

        # Статистика за час
        stats = dashboard_data.get('statistics', {})
        if stats:
            print(f"\n📈 СРЕДНИЕ ЗНАЧЕНИЯ ЗА ЧАС:")
            print(f"   CPU: {stats['avg_cpu']:.1f}%")
            print(f"   Память: {stats['avg_memory']:.1f}%")
            print(f"   Отклик: {stats['avg_response_time']:.0f}ms")
            print(f"   Пик заказов: {stats['peak_orders']}")

        # Активные алерты
        alerts = dashboard_data.get('active_alerts', [])
        if alerts:
            print(f"\n🚨 АКТИВНЫЕ АЛЕРТЫ ({len(alerts)}):")
            for alert in alerts[:5]:  # Показываем только 5 последних
                severity_emoji = "🚨" if alert[3] == 'critical' else "⚠️"
                print(f"   {severity_emoji} {alert[4]}")
        else:
            print(f"\n✅ Активных алертов нет")

        # Метрики ботов
        print(f"\n🤖 СОСТОЯНИЕ БОТОВ:")
        for bot_name, bot_metrics in self._bot_metrics.items():
            print(f"   {bot_name}:")
            print(f"     📨 Сообщений: {bot_metrics.messages_sent}")
            print(f"     👥 Активных пользователей: {bot_metrics.active_users}")
            print(f"     ❌ Ошибок: {bot_metrics.errors_count}")
            print(f"     🧠 Память: {bot_metrics.memory_mb:.1f} MB")

        print("=" * 60)

    def cleanup_old_metrics(self, days: int = 30):
        """Удаляет старые метрики"""

        conn = sqlite3.connect(self.monitoring_db)

        try:
            # Удаляем старые системные метрики
            cursor = conn.execute("""
                DELETE FROM system_metrics 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days))
            deleted_system = cursor.rowcount

            # Удаляем старые метрики ботов
            cursor = conn.execute("""
                DELETE FROM bot_metrics 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days))
            deleted_bots = cursor.rowcount

            # Удаляем старые алерты
            cursor = conn.execute("""
                DELETE FROM alerts 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days))
            deleted_alerts = cursor.rowcount

            conn.commit()

            print(f"🗑️ Очистка метрик старше {days} дней:")
            print(f"   Системных: {deleted_system}")
            print(f"   Ботов: {deleted_bots}")
            print(f"   Алертов: {deleted_alerts}")

        except Exception as e:
            print(f"❌ Ошибка очистки метрик: {e}")
        finally:
            conn.close()

    def start_monitoring(self, interval: int = 60):
        """Запускает мониторинг в отдельном потоке"""

        def monitoring_loop():
            while True:
                try:
                    # Сохраняем метрики
                    self.save_metrics()

                    # Проверяем алерты
                    self.check_alerts()

                    time.sleep(interval)

                except Exception as e:
                    print(f"❌ Ошибка в цикле мониторинга: {e}")
                    time.sleep(interval)

        thread = threading.Thread(target=monitoring_loop, daemon=True)
        thread.start()
        print(f"🚀 Мониторинг запущен (интервал: {interval}s)")


# Декоратор для измерения времени выполнения
@asynccontextmanager
async def measure_time(monitor: PerformanceMonitor, operation: str):
    """Контекстный менеджер для измерения времени операций"""
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # в миллисекундах
        monitor.record_response_time(response_time)
        print(f"⏱️ {operation}: {response_time:.0f}ms")


def sync_measure_time(monitor: PerformanceMonitor, operation: str):
    """Декоратор для синхронных функций"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                monitor.record_response_time(response_time)
                print(f"⏱️ {operation}: {response_time:.0f}ms")

        return wrapper

    return decorator


# Глобальный экземпляр монитора
performance_monitor = PerformanceMonitor()


# Функции для интеграции с ботами
def track_message_sent(bot_name: str):
    """Отслеживает отправленное сообщение"""
    performance_monitor.counters['messages_sent'] += 1


def track_message_received(bot_name: str):
    """Отслеживает полученное сообщение"""
    performance_monitor.counters['messages_received'] += 1


def track_order_created():
    """Отслеживает создание заказа"""
    performance_monitor.counters['orders_created'] += 1


def track_order_completed():
    """Отслеживает завершение заказа"""
    performance_monitor.counters['orders_completed'] += 1


def track_error(error_type: str = "general"):
    """Отслеживает ошибку"""
    performance_monitor.counters['errors'] += 1


# CLI интерфейс
def main():
    import sys

    if len(sys.argv) < 2:
        print("📊 СИСТЕМА МОНИТОРИНГА ТАКСИ-БОТОВ")
        print("=" * 40)
        print("Доступные команды:")
        print("  dashboard        - Показать дашборд")
        print("  start [interval] - Запустить мониторинг")
        print("  cleanup [days]   - Очистить старые метрики")
        print("  alerts          - Показать активные алерты")
        print("  stats [hours]   - Статистика за период")
        return

    command = sys.argv[1]

    if command == "dashboard":
        performance_monitor.print_dashboard()

    elif command == "start":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        performance_monitor.start_monitoring(interval)

        print("📊 Мониторинг запущен. Нажмите Ctrl+C для остановки.")
        print("Дашборд обновляется каждые 30 секунд...")

        try:
            while True:
                time.sleep(30)
                performance_monitor.print_dashboard()
        except KeyboardInterrupt:
            print("\n🛑 Мониторинг остановлен")

    elif command == "cleanup":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        performance_monitor.cleanup_old_metrics(days)

    elif command == "alerts":
        dashboard_data = performance_monitor.get_dashboard_data(24)
        alerts = dashboard_data.get('active_alerts', [])

        if alerts:
            print(f"🚨 АКТИВНЫЕ АЛЕРТЫ ({len(alerts)}):")
            for alert in alerts:
                severity_emoji = "🚨" if alert[3] == 'critical' else "⚠️"
                timestamp = alert[1]
                message = alert[4]
                print(f"{severity_emoji} {timestamp}: {message}")
        else:
            print("✅ Активных алертов нет")

    elif command == "stats":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        dashboard_data = performance_monitor.get_dashboard_data(hours)
        stats = dashboard_data.get('statistics', {})

        print(f"📈 СТАТИСТИКА ЗА ПОСЛЕДНИЕ {hours} ЧАСОВ:")
        print("=" * 50)
        print(f"💻 Средняя загрузка CPU: {stats.get('avg_cpu', 0):.1f}%")
        print(f"🧠 Среднее использование памяти: {stats.get('avg_memory', 0):.1f}%")
        print(f"⚡ Среднее время отклика: {stats.get('avg_response_time', 0):.0f}ms")
        print(f"📦 Пиковое количество заказов/мин: {stats.get('peak_orders', 0)}")
        print(f"⏱️  Время работы: {str(timedelta(seconds=dashboard_data.get('uptime_seconds', 0)))}")

    else:
        print(f"❌ Неизвестная команда: {command}")


if __name__ == "__main__":
    main()