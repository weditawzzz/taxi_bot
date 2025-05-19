from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from core.keyboards import language_keyboard
from core.keyboards import main_menu_keyboard
from core.services.user_service import get_or_create_user, update_user_language
from core.models import Session, User
import json
import os

router = Router()


def get_localization(lang: str, key: str) -> str:
    with open(f'locales/{lang}.json', 'r', encoding='utf-8') as f:
        translations = json.load(f)
    return translations.get(key, key)


@router.message(CommandStart())
async def start_command(message: Message):
    user = get_or_create_user(message.from_user.id)
    await message.answer(
        "Выберите язык / Choose language / Wybierz język:",
        reply_markup=language_keyboard()
    )


@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery):
    lang_code = callback.data.split("_")[1]

    with Session() as session:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        if not user:
            user = User(telegram_id=callback.from_user.id, language=lang_code)
            session.add(user)
        else:
            user.language = lang_code
        session.commit()

    # Используем ключ "start" вместо "welcome"
    greeting = get_localization(lang_code, "start")

    await callback.message.edit_text(
        text=f"✅ {greeting}",  # Будет "Witaj! Wybierz usługę:"
        reply_markup=main_menu_keyboard(lang_code)
    )