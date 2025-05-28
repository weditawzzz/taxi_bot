#!/usr/bin/env python3
"""
Исправленная система бэкапов для такси-ботов
ИСПРАВЛЕНО: Автоматическое создание папок
"""

import shutil
import sqlite3
import zipfile
import json
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time


class BackupSystem:
    """Система автоматического резервного копирования"""

    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)

        # ИСПРАВЛЕНО: Создаем папки для разных типов бэкапов
        self.daily_dir = self.backup_dir / "daily"
        self.weekly_dir = self.backup_dir / "weekly"
        self.monthly_dir = self.backup_dir / "monthly"
        self.manual_dir = self.backup_dir / "manual"

        # Создаем все папки
        self.daily_dir.mkdir(exist_ok=True)
        self.weekly_dir.mkdir(exist_ok=True)
        self.monthly_dir.mkdir(exist_ok=True)
        self.manual_dir.mkdir(exist_ok=True)

        self.data_dir = Path("data")
        self.logs_dir = Path("logs")

    def create_full_backup(self, backup_type: str = "manual") -> str:
        """Создает полный бэкап системы"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"taxi_backup_{backup_type}_{timestamp}.zip"

        # ИСПРАВЛЕНО: Определяем правильную папку
        if backup_type == "daily":
            backup_folder = self.daily_dir
        elif backup_type == "weekly":
            backup_folder = self.weekly_dir
        elif backup_type == "monthly":
            backup_folder = self.monthly_dir
        else:
            backup_folder = self.manual_dir

        # Убеждаемся что папка существует
        backup_folder.mkdir(exist_ok=True)

        backup_path = backup_folder / backup_filename

        print(f"📦 Создание {backup_type} бэкапа...")
        print(f"📁 Путь: {backup_path}")

        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:

                # 1. Базы данных
                if self.data_dir.exists():
                    print("💾 Копирование баз данных...")
                    for db_file in self.data_dir.glob("*.db"):
                        # Создаем дамп SQLite для надежности
                        dump_path = self.create_db_dump(db_file)
                        if dump_path:
                            backup_zip.write(dump_path, f"database_dumps/{dump_path.name}")
                            dump_path.unlink()  # Удаляем временный файл
                            print(f"  ✅ Дамп: {db_file.name}")

                        # Также копируем оригинальный файл
                        backup_zip.write(db_file, f"databases/{db_file.name}")
                        print(f"  ✅ База: {db_file.name}")
                else:
                    print("⚠️ Папка data не найдена")

                # 2. Конфигурационные файлы
                print("⚙️ Копирование конфигов...")
                config_files = [
                    "config.py",
                    ".env",
                    "requirements.txt",
                    "driver_bot.py",
                    "run.py"
                ]

                for config_file in config_files:
                    config_path = Path(config_file)
                    if config_path.exists():
                        backup_zip.write(config_path, f"config/{config_file}")
                        print(f"  ✅ {config_file}")

                # 3. Логи (только последние 7 дней)
                if self.logs_dir.exists():
                    print("📋 Копирование логов...")
                    cutoff_date = datetime.now() - timedelta(days=7)
                    log_count = 0
                    for log_file in self.logs_dir.glob("*.log*"):
                        if log_file.stat().st_mtime > cutoff_date.timestamp():
                            backup_zip.write(log_file, f"logs/{log_file.name}")
                            log_count += 1
                    print(f"  ✅ Логов: {log_count}")
                else:
                    print("📋 Папка logs не найдена")

                # 4. Системная информация
                print("ℹ️ Сохранение системной информации...")
                system_info = self.collect_system_info()
                info_json = json.dumps(system_info, indent=2, ensure_ascii=False)
                backup_zip.writestr("system_info.json", info_json)

            backup_size = backup_path.stat().st_size / (1024 * 1024)  # MB

            print(f"✅ Бэкап создан: {backup_filename}")
            print(f"📁 Размер: {backup_size:.1f} MB")
            print(f"📍 Полный путь: {backup_path.absolute()}")

            # Записываем информацию о бэкапе
            self.log_backup(backup_type, backup_filename, backup_size)

            return str(backup_path)

        except Exception as e:
            print(f"❌ Ошибка создания бэкапа: {e}")
            print(f"🔍 Отладочная информация:")
            print(f"   Папка бэкапа: {backup_folder}")
            print(f"   Папка существует: {backup_folder.exists()}")
            print(f"   Права записи: {backup_folder.parent.exists()}")
            return None

    def create_db_dump(self, db_path: Path) -> Path:
        """Создает SQL дамп базы данных"""
        try:
            # ИСПРАВЛЕНО: Создаем временную папку
            temp_dir = self.backup_dir / "temp"
            temp_dir.mkdir(exist_ok=True)

            dump_path = temp_dir / f"{db_path.stem}_dump.sql"

            with sqlite3.connect(db_path) as conn:
                with open(dump_path, 'w', encoding='utf-8') as f:
                    for line in conn.iterdump():
                        f.write(f"{line}\n")

            return dump_path

        except Exception as e:
            print(f"❌ Ошибка создания дампа {db_path}: {e}")
            return None

    def collect_system_info(self) -> dict:
        """Собирает информацию о системе"""
        info = {
            "backup_timestamp": datetime.now().isoformat(),
            "python_version": "",
            "database_stats": {},
            "system_stats": {}
        }

        try:
            import sys
            info["python_version"] = sys.version

            # Статистика баз данных
            if self.data_dir.exists():
                for db_file in self.data_dir.glob("*.db"):
                    try:
                        conn = sqlite3.connect(db_file)
                        cursor = conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        )
                        tables = [row[0] for row in cursor.fetchall()]

                        table_stats = {}
                        for table in tables:
                            try:
                                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                                count = cursor.fetchone()[0]
                                table_stats[table] = count
                            except:
                                table_stats[table] = "error"

                        info["database_stats"][db_file.name] = {
                            "tables": tables,
                            "row_counts": table_stats,
                            "file_size_mb": db_file.stat().st_size / (1024 * 1024)
                        }

                        conn.close()

                    except Exception as e:
                        info["database_stats"][db_file.name] = {"error": str(e)}

            # Размеры папок
            if self.data_dir.exists():
                info["system_stats"]["data_dir_size_mb"] = self.get_dir_size(self.data_dir)

            if self.logs_dir.exists():
                info["system_stats"]["logs_dir_size_mb"] = self.get_dir_size(self.logs_dir)

        except Exception as e:
            info["collection_error"] = str(e)

        return info

    def get_dir_size(self, path: Path) -> float:
        """Получает размер папки в MB"""
        total = 0
        try:
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    total += file_path.stat().st_size
        except Exception:
            pass
        return total / (1024 * 1024)

    def log_backup(self, backup_type: str, filename: str, size_mb: float):
        """Записывает информацию о бэкапе"""
        log_file = self.backup_dir / "backup_log.json"

        backup_record = {
            "timestamp": datetime.now().isoformat(),
            "type": backup_type,
            "filename": filename,
            "size_mb": round(size_mb, 2),
            "status": "success"
        }

        try:
            # Читаем существующий лог
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
            else:
                log_data = {"backups": []}

            # Добавляем новую запись
            log_data["backups"].append(backup_record)

            # Оставляем только последние 100 записей
            log_data["backups"] = log_data["backups"][-100:]

            # Записываем обратно
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"⚠️ Ошибка записи лога бэкапа: {e}")

    def show_backup_status(self):
        """Показывает статус бэкапов"""

        print("📊 СТАТУС СИСТЕМЫ БЭКАПОВ")
        print("=" * 50)

        # Показываем последние бэкапы
        backup_types = {
            "manual": self.manual_dir,
            "daily": self.daily_dir,
            "weekly": self.weekly_dir,
            "monthly": self.monthly_dir
        }

        for backup_type, backup_folder in backup_types.items():
            if backup_folder.exists():
                backups = sorted(
                    backup_folder.glob("taxi_backup_*.zip"),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )

                if backups:
                    latest = backups[0]
                    backup_time = datetime.fromtimestamp(latest.stat().st_mtime)
                    size_mb = latest.stat().st_size / (1024 * 1024)

                    print(f"📦 {backup_type.title()}: {backup_time.strftime('%Y-%m-%d %H:%M')} ({size_mb:.1f} MB)")
                    print(f"   Всего бэкапов: {len(backups)}")
                else:
                    print(f"📦 {backup_type.title()}: Нет бэкапов")
            else:
                print(f"📦 {backup_type.title()}: Папка не существует")

        # Общий размер бэкапов
        total_size = self.get_dir_size(self.backup_dir)
        print(f"\n💾 Общий размер бэкапов: {total_size:.1f} MB")

        # Читаем лог
        log_file = self.backup_dir / "backup_log.json"
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)

                recent_backups = log_data.get("backups", [])[-5:]

                if recent_backups:
                    print(f"\n📋 Последние бэкапы:")
                    for backup in reversed(recent_backups):
                        timestamp = datetime.fromisoformat(backup["timestamp"])
                        print(
                            f"   • {timestamp.strftime('%Y-%m-%d %H:%M')} - {backup['type']} ({backup['size_mb']} MB)")

            except Exception as e:
                print(f"⚠️ Ошибка чтения лога: {e}")

    def cleanup_old_backups(self):
        """Удаляет старые бэкапы"""

        cleanup_rules = {
            "daily": 7,  # Хранить 7 дней
            "weekly": 4,  # Хранить 4 недели
            "monthly": 12,  # Хранить 12 месяцев
            "manual": 20  # Хранить 20 ручных бэкапов
        }

        for backup_type, keep_count in cleanup_rules.items():
            if backup_type == "daily":
                backup_folder = self.daily_dir
            elif backup_type == "weekly":
                backup_folder = self.weekly_dir
            elif backup_type == "monthly":
                backup_folder = self.monthly_dir
            else:
                backup_folder = self.manual_dir

            if not backup_folder.exists():
                continue

            # Получаем список бэкапов, отсортированный по дате
            backups = sorted(
                backup_folder.glob("taxi_backup_*.zip"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            # Удаляем старые бэкапы
            to_delete = backups[keep_count:]

            for backup_file in to_delete:
                try:
                    backup_file.unlink()
                    print(f"🗑️ Удален старый бэкап: {backup_file.name}")
                except Exception as e:
                    print(f"❌ Ошибка удаления {backup_file.name}: {e}")


# Глобальный экземпляр системы
backup_system = BackupSystem()


# CLI интерфейс
def main():
    import sys

    if len(sys.argv) < 2:
        print("💾 СИСТЕМА БЭКАПОВ ТАКСИ-БОТОВ")
        print("=" * 40)
        print("Доступные команды:")
        print("  create [type]    - Создать бэкап (daily/weekly/monthly/manual)")
        print("  status          - Показать статус бэкапов")
        print("  cleanup         - Очистить старые бэкапы")
        print("")
        print("Примеры:")
        print("  python backup_system.py create manual")
        print("  python backup_system.py status")
        return

    command = sys.argv[1]

    if command == "create":
        backup_type = sys.argv[2] if len(sys.argv) > 2 else "manual"
        result = backup_system.create_full_backup(backup_type)
        if result:
            print(f"🎉 Бэкап успешно создан!")
        else:
            print(f"❌ Ошибка создания бэкапа")

    elif command == "status":
        backup_system.show_backup_status()

    elif command == "cleanup":
        backup_system.cleanup_old_backups()
        print("✅ Очистка завершена")

    else:
        print(f"❌ Неизвестная команда: {command}")
        print("Используйте: create, status, cleanup")


if __name__ == "__main__":
    main()