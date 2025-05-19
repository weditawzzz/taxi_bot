from core.models import Session, User
import json
from pathlib import Path
from core.models import Session, User

# Добавляем функцию локализации
def get_localization(lang: str, key: str) -> str:
    try:
        locales_path = Path(__file__).parent.parent.parent / "locales" / f"{lang}.json"
        with open(locales_path, "r", encoding="utf-8") as f:
            translations = json.load(f)
        return translations.get(key, key)
    except Exception as e:
        print(f"Localization error: {e}")
        return key

def get_or_create_user(telegram_id: int) -> User:
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id)
            session.add(user)
            session.commit()
        else:
            session.refresh(user)  # Обновляем объект
        return user

def update_user_language(telegram_id: int, lang_code: str):
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.language = lang_code
            session.commit()

def get_user_language(telegram_id: int) -> str:
    """Возвращает язык пользователя по его telegram_id"""
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        return user.language if user else 'pl'  # По умолчанию польский