# core/handlers/driver/driver_start.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from core.keyboards import language_keyboard
from core.handlers.driver.vehicle_handlers import get_vehicle_keyboard
from core.services.user_service import get_or_create_user, get_user_language
from core.models import Session, User
from core.utils.localization import get_localization

router = Router()


@router.message(CommandStart())
async def driver_start(message: Message):
    await message.answer(
        "Выберите язык (водитель):",
        reply_markup=language_keyboard()
    )


@router.callback_query(F.data.startswith("lang_"))
async def set_driver_language(callback: CallbackQuery):
    lang_code = callback.data.split("_")[1]

    with Session() as session:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        if not user:
            user = User(telegram_id=callback.from_user.id, language=lang_code)
            session.add(user)
        else:
            user.language = lang_code
        session.commit()

    await callback.message.edit_text(
        text="🚖 Панель водителя",
        reply_markup=get_vehicle_keyboard(lang_code)
    )