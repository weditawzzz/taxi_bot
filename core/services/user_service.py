"""
Сервис для работы с пользователями
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import User, UserRole
from core.database import get_session
from core.exceptions import ValidationError, NotFoundError, ServiceError

logger = logging.getLogger(__name__)


class UserService:
    """Сервис для работы с пользователями"""

    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: UserRole = UserRole.CLIENT
    ) -> User:
        """Получить или создать пользователя"""
        try:
            async with get_session() as session:
                # Ищем существующего пользователя
                stmt = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if user:
                    # Обновляем информацию если изменилась
                    updated = False
                    if username and user.username != username:
                        user.username = username
                        updated = True
                    if first_name and user.first_name != first_name:
                        user.first_name = first_name
                        updated = True
                    if last_name and user.last_name != last_name:
                        user.last_name = last_name
                        updated = True

                    user.last_seen = datetime.utcnow()
                    updated = True

                    if updated:
                        await session.commit()

                    return user

                # Создаем нового пользователя
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    last_seen=datetime.utcnow()
                )

                session.add(user)
                await session.commit()
                await session.refresh(user)

                logger.info(f"Created new user: {telegram_id} ({role})")
                return user

        except Exception as e:
            logger.error(f"Error creating/updating user {telegram_id}: {e}")
            raise ServiceError("Failed to create or update user")

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID"""
        try:
            async with get_session() as session:
                stmt = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting user {telegram_id}: {e}")
            raise ServiceError("Failed to get user")

    async def update_user_language(self, telegram_id: int, language: str) -> None:
        """Обновить язык пользователя"""
        try:
            if language not in ['en', 'pl', 'ru']:
                raise ValidationError(f"Unsupported language: {language}")

            async with get_session() as session:
                stmt = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    raise NotFoundError(f"User not found: {telegram_id}")

                user.language = language
                await session.commit()

        except Exception as e:
            logger.error(f"Error updating user language {telegram_id}: {e}")
            raise ServiceError("Failed to update user language")