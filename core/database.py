"""
Управление базой данных
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession, AsyncEngine, async_sessionmaker, create_async_engine
)

from .models import Base
from .config import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер базы данных"""

    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    @property
    def engine(self) -> AsyncEngine:
        """Получить движок базы данных"""
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Получить фабрику сессий"""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory

    async def initialize(self) -> None:
        """Инициализация базы данных"""
        try:
            logger.info("Initializing database connection...")

            # Создаем движок
            self._engine = create_async_engine(
                config.database.url,
                echo=config.database.echo,
            )

            # Создаем фабрику сессий
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
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
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    async def close(self) -> None:
        """Закрытие соединения с базой данных"""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database connection closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Контекстный менеджер для получения сессии"""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


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
    """Получить сессию базы данных"""
    async with db_manager.get_session() as session:
        yield session