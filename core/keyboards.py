from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.services.user_service import get_localization


def language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇵🇱 Polski", callback_data="lang_pl")
    builder.button(text="🇬🇧 English", callback_data="lang_en")
    builder.button(text="🇷🇺 Русский", callback_data="lang_ru")
    builder.adjust(3)
    return builder.as_markup()


def main_menu_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    texts = [
        ("city_ride", "🚖 Поездка по городу"),
        ("airport", "✈️ Аэропорт"),
        ("alcohol", "🍷 Доставка алкоголя"),
        ("intercity", "🚗 Междугородние"),
        ("international", "🌍 Международные")
    ]

    for key, default_text in texts:
        text = get_localization(lang, key) or default_text
        builder.button(text=text, callback_data=f"menu_{key}")

    builder.adjust(2, 2, 1)
    return builder.as_markup()


def confirm_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_localization(lang, "yes"),  # Будет использовать перевод
        callback_data="confirm_yes"
    )
    builder.button(
        text=get_localization(lang, "no"),
        callback_data="confirm_no"
    )
    return builder.as_markup()

def payment_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_localization(lang, "cash"),
        callback_data="payment_cash"
    )
    builder.button(
        text="USDT",
        callback_data="payment_usdt"
    )
    builder.adjust(2)
    return builder.as_markup()