from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from core.keyboards import language_keyboard  # Исправленный импорт
from core.handlers.driver.vehicle_handlers import get_vehicle_keyboard
from core.services.user_service import UserService  # Исправленный импорт
from core.models import Session, User

router = Router()


async def get_user_language(user_id: int) -> str:
    """Простая функция получения языка пользователя"""
    try:
        user_service = UserService()
        user = await user_service.get_user_by_telegram_id(user_id)
        return user.language if user and user.language else "pl"
    except Exception:
        return "pl"


@router.message(CommandStart())
async def driver_start(message: Message):
    await message.answer(
        "Выберите язык (водитель):",
        reply_markup=language_keyboard()
    )


@router.callback_query(F.data.startswith("lang_"))
async def set_driver_language(callback: CallbackQuery):
    lang_code = callback.data.split("_")[1]

    try:
        # Используем новый UserService
        user_service = UserService()

        # Сначала пытаемся получить пользователя
        user = await user_service.get_user_by_telegram_id(callback.from_user.id)

        if not user:
            # Если пользователя нет, создаем нового
            from core.models import UserRole
            user = await user_service.get_or_create_user(
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name,
                role=UserRole.DRIVER
            )

        # Обновляем язык
        await user_service.update_user_language(callback.from_user.id, lang_code)

    except Exception as e:
        print(f"Ошибка обновления языка: {e}")
        # Fallback - используем синхронную сессию
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
            if not user:
                from core.models import UserRole
                user = User(
                    telegram_id=callback.from_user.id,
                    username=callback.from_user.username,
                    first_name=callback.from_user.first_name,
                    last_name=callback.from_user.last_name,
                    language=lang_code,
                    role=UserRole.DRIVER
                )
                session.add(user)
            else:
                user.language = lang_code
            session.commit()

    await callback.message.edit_text(
        text="🚖 Панель водителя",
        reply_markup=get_vehicle_keyboard(lang_code)
    )