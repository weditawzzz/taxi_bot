"""
Управление базой данных с поддержкой синхронных и асинхронных операций
"""
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Optional, Generator

from sqlalchemy.ext.asyncio import (
    AsyncSession, AsyncEngine, async_sessionmaker, create_async_engine
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SyncSession

from .models import Base
from .config import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер базы данных"""

    def __init__(self):
        self._async_engine: Optional[AsyncEngine] = None
        self._sync_engine: Optional[create_engine] = None
        self._async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._sync_session_factory: Optional[sessionmaker[SyncSession]] = None

    @property
    def async_engine(self) -> AsyncEngine:
        """Получить асинхронный движок базы данных"""
        if self._async_engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._async_engine

    @property
    def sync_engine(self):
        """Получить синхронный движок базы данных"""
        if self._sync_engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._sync_engine

    @property
    def async_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Получить фабрику асинхронных сессий"""
        if self._async_session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._async_session_factory

    @property
    def sync_session_factory(self) -> sessionmaker[SyncSession]:
        """Получить фабрику синхронных сессий"""
        if self._sync_session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._sync_session_factory

    async def initialize(self) -> None:
        """Инициализация базы данных"""
        try:
            logger.info("Initializing database connection...")

            # Создаем асинхронный движок
            engine_kwargs = {
                'echo': config.database.echo,
            }

            # Connection pooling только для PostgreSQL/MySQL, не для SQLite
            if not config.database.url.startswith('sqlite'):
                engine_kwargs.update({
                    'pool_size': 20,
                    'max_overflow': 30,
                    'pool_pre_ping': True,
                    'pool_recycle': 3600
                })

            self._async_engine = create_async_engine(
                config.database.url,
                **engine_kwargs
            )

            # Создаем синхронный движок для обратной совместимости
            sync_url = config.database.url.replace('sqlite+aiosqlite:', 'sqlite:')
            sync_engine_kwargs = {
                'echo': config.database.echo,
            }

            # Connection pooling только для PostgreSQL/MySQL, не для SQLite
            if not sync_url.startswith('sqlite'):
                sync_engine_kwargs.update({
                    'pool_pre_ping': True,
                    'pool_recycle': 3600
                })

            self._sync_engine = create_engine(
                sync_url,
                **sync_engine_kwargs
            )

            # Создаем фабрики сессий
            self._async_session_factory = async_sessionmaker(
                bind=self._async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            self._sync_session_factory = sessionmaker(
                bind=self._sync_engine,
                expire_on_commit=False
            )

            # Создаем таблицы если их нет
            await self.create_tables()

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def create_tables(self) -> None:
        """Создание таблиц"""
        try:
            # Создаем таблицы асинхронно
            async with self._async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Также создаем синхронно для совместимости
            Base.metadata.create_all(self._sync_engine)

            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    async def close(self) -> None:
        """Закрытие соединения с базой данных"""
        if self._async_engine:
            await self._async_engine.dispose()
        if self._sync_engine:
            self._sync_engine.dispose()
        logger.info("Database connections closed")

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Контекстный менеджер для получения асинхронной сессии"""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @contextmanager
    def get_sync_session(self) -> Generator[SyncSession, None, None]:
        """Контекстный менеджер для получения синхронной сессии"""
        session = self.sync_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Глобальный экземпляр менеджера
db_manager = DatabaseManager()


async def init_database() -> None:
    """Инициализация базы данных"""
    await db_manager.initialize()


async def close_database() -> None:
    """Закрытие базы данных"""
    await db_manager.close()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Получить асинхронную сессию базы данных"""
    async with db_manager.get_async_session() as session:
        yield session


@contextmanager
def get_sync_session() -> Generator[SyncSession, None, None]:
    """Получить синхронную сессию базы данных"""
    with db_manager.get_sync_session() as session:
        yield session


# ============================================
# ОБРАТНАЯ СОВМЕСТИМОСТЬ
# ============================================

class SessionContext:
    """Контекстный менеджер для совместимости с old Session()"""

    def __enter__(self):
        self._session = db_manager.sync_session_factory()
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                self._session.commit()
            else:
                self._session.rollback()
        finally:
            self._session.close()


# Алиас для старого кода: with Session() as session:
Session = SessionContext