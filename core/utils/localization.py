"""
Локализация текстов
"""
from enum import Enum
from typing import Dict, Any


class Language(str, Enum):
    """Поддерживаемые языки"""
    PL = "pl"
    RU = "ru"
    EN = "en"


# Словарь переводов
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # Приветствие и основное
    "welcome_client": {
        "pl": "Witaj {name}! 👋\n\nJestem botem taxi w Szczecinie. Mogę pomóc Ci zamówić taxi szybko i wygodnie.\n\nWybierz opcję z menu:",
        "ru": "Добро пожаловать, {name}! 👋\n\nЯ бот такси в Щецине. Помогу вам быстро и удобно заказать такси.\n\nВыберите опцию из меню:",
        "en": "Welcome {name}! 👋\n\nI'm a taxi bot in Szczecin. I can help you order a taxi quickly and conveniently.\n\nChoose an option from the menu:"
    },

    "welcome_driver": {
        "pl": "Witaj {name}! 👋\n\nJestem botem dla kierowców taxi w Szczecinie.\n\nWybierz opcję z menu:",
        "ru": "Добро пожаловать, {name}! 👋\n\nЯ бот для водителей такси в Щецине.\n\nВыберите опцию из меню:",
        "en": "Welcome {name}! 👋\n\nI'm a bot for taxi drivers in Szczecin.\n\nChoose an option from the menu:"
    },

    "main_menu": {
        "pl": "Menu główne",
        "ru": "Главное меню",
        "en": "Main menu"
    },

    # Заказ такси
    "send_pickup_location": {
        "pl": "📍 Gdzie Cię zabrać?\n\nWyślij swoją lokalizację lub wpisz adres:",
        "ru": "📍 Откуда вас забрать?\n\nОтправьте свою локацию или введите адрес:",
        "en": "📍 Where should I pick you up?\n\nSend your location or enter the address:"
    },

    "send_destination_location": {
        "pl": "📍 Dokąd chcesz pojechać?\n\nWyślij lokalizację lub wpisz adres:",
        "ru": "📍 Куда вы хотите поехать?\n\nОтправьте локацию или введите адрес:",
        "en": "📍 Where do you want to go?\n\nSend location or enter the address:"
    },

    "enter_pickup_address": {
        "pl": "✍️ Wpisz adres miejsca odbioru:",
        "ru": "✍️ Введите адрес места подачи:",
        "en": "✍️ Enter pickup address:"
    },

    "enter_destination_address": {
        "pl": "✍️ Wpisz adres miejsca docelowego:",
        "ru": "✍️ Введите адрес места назначения:",
        "en": "✍️ Enter destination address:"
    },

    "enter_passengers_count": {
        "pl": "👥 Ile osób będzie jechać?",
        "ru": "👥 Сколько человек будет ехать?",
        "en": "👥 How many people will be traveling?"
    },

    "ride_summary": {
        "pl": "🚖 <b>Podsumowanie zamówienia:</b>\n\n📍 <b>Z:</b> {pickup}\n📍 <b>Do:</b> {destination}\n\n📏 <b>Dystans:</b> {distance} km\n⏱ <b>Czas:</b> {duration} min\n👥 <b>Pasażerów:</b> {passengers}\n\n💰 <b>Szacowana cena:</b> {price} PLN\n\n✅ Potwierdź zamówienie?",
        "ru": "🚖 <b>Сводка заказа:</b>\n\n📍 <b>Откуда:</b> {pickup}\n📍 <b>Куда:</b> {destination}\n\n📏 <b>Расстояние:</b> {distance} км\n⏱ <b>Время:</b> {duration} мин\n👥 <b>Пассажиров:</b> {passengers}\n\n💰 <b>Примерная цена:</b> {price} PLN\n\n✅ Подтвердить заказ?",
        "en": "🚖 <b>Order Summary:</b>\n\n📍 <b>From:</b> {pickup}\n📍 <b>To:</b> {destination}\n\n📏 <b>Distance:</b> {distance} km\n⏱ <b>Time:</b> {duration} min\n👥 <b>Passengers:</b> {passengers}\n\n💰 <b>Estimated price:</b> {price} PLN\n\n✅ Confirm order?"
    },

    "ride_created": {
        "pl": "✅ <b>Zamówienie zostało utworzone!</b>\n\n🆔 Numer zamówienia: <code>{ride_id}</code>\n\n🔍 Szukamy dostępnego kierowcy...\nOczekiwany czas oczekiwania: 2-5 minut",
        "ru": "✅ <b>Заказ создан!</b>\n\n🆔 Номер заказа: <code>{ride_id}</code>\n\n🔍 Ищем доступного водителя...\nОжидаемое время ожидания: 2-5 минут",
        "en": "✅ <b>Order created!</b>\n\n🆔 Order number: <code>{ride_id}</code>\n\n🔍 Looking for available driver...\nExpected waiting time: 2-5 minutes"
    },

    "no_drivers_available": {
        "pl": "😞 Przepraszamy, obecnie brak dostępnych kierowców.\n\nSpróbuj ponownie za kilka minut.",
        "ru": "😞 Извините, в данный момент нет доступных водителей.\n\nПовторите попытку через несколько минут.",
        "en": "😞 Sorry, no drivers available at the moment.\n\nPlease try again in a few minutes."
    },

    "order_cancelled": {
        "pl": "❌ Zamówienie zostało anulowane.",
        "ru": "❌ Заказ отменен.",
        "en": "❌ Order cancelled."
    },

    # НОВЫЕ ПЕРЕВОДЫ ДЛЯ АЛКОГОЛЯ
    "enter_shopping_list": {
        "pl": "🛒 Wprowadź listę zakupów (np. 1x Żubr 0.5L, 2x Żywiec, 1x Vodka):",
        "ru": "🛒 Введите список покупок (напр. 1x Пиво 0.5Л, 2x Водка, 1x Вино):",
        "en": "🛒 Enter shopping list (e.g. 1x Beer 0.5L, 2x Vodka, 1x Wine):"
    },

    "enter_budget": {
        "pl": "💰 Podaj maksymalny budżet na zakupy (w zł):",
        "ru": "💰 Укажите максимальный бюджет на покупки (в zł):",
        "en": "💰 Enter maximum budget for purchases (in zł):"
    },

    "invalid_budget": {
        "pl": "❌ Nieprawidłowy budżet! Wprowadź liczbę:",
        "ru": "❌ Неверный бюджет! Введите число:",
        "en": "❌ Invalid budget! Enter a number:"
    },

    "budget_too_low": {
        "pl": "❌ Minimalna kwota zakupów to 20 zł",
        "ru": "❌ Минимальная сумма покупок 20 zł",
        "en": "❌ Minimum purchase amount is 20 zł"
    },

    "confirm_age": {
        "pl": "🔞 Czy masz ukończone 18 lat?",
        "ru": "🔞 Вам есть 18 лет?",
        "en": "🔞 Are you 18+ years old?"
    },

    "age_warning": {
        "pl": "🚫 Dostawa alkoholu możliwa tylko dla osób pełnoletnich!",
        "ru": "🚫 Доставка алкоголя только для совершеннолетних!",
        "en": "🚫 Alcohol delivery only for adults!"
    },

    "enter_alcohol_address": {
        "pl": "📍 Podaj adres dostawy:",
        "ru": "📍 Укажите адрес доставки:",
        "en": "📍 Enter delivery address:"
    },

    "alcohol_shop_tariff_info": {
        "pl": "🚚 <b>Zakup i dostawa alkoholu:</b>\n\n• Opłata za usługę: 25 zł + 15 zł\n• Opłata za km: 3 zł/km\n• Taryfa nocna (22:00-6:00): +30%\n• Dodatkowo: koszt zakupów\n• Płatność <u>wyłącznie gotówką</u>",
        "ru": "🚚 <b>Покупка и доставка алкоголя:</b>\n\n• Плата за услугу: 25 zł + 15 zł\n• Плата за км: 3 zł/км\n• Ночной тариф (22:00-6:00): +30%\n• Дополнительно: стоимость покупок\n• Оплата <u>только наличными</u>",
        "en": "🚚 <b>Alcohol purchase and delivery:</b>\n\n• Service fee: 25 zł + 15 zł\n• Fee per km: 3 zł/km\n• Night tariff (22:00-6:00): +30%\n• Additionally: purchase cost\n• Payment <u>cash only</u>"
    },

    "alcohol_cash_only": {
        "pl": "⚠️ <b>Uwaga!</b> Przy dostawie alkoholu możliwa jest <u>wyłącznie płatność gotówką</u>!",
        "ru": "⚠️ <b>Внимание!</b> При доставке алкоголя возможна <u>только оплата наличными</u>!",
        "en": "⚠️ <b>Attention!</b> For alcohol delivery <u>only cash payment</u> is possible!"
    },

    "alcohol_shop_receipt_info": {
        "pl": "📝 <b>Uwaga!</b> Kierowca kupi alkohol w wybranym sklepie i przywiezie paragon. Koszt zakupów należy opłacić <u>dodatkowo</u> do opłaty za usługę.",
        "ru": "📝 <b>Внимание!</b> Водитель купит алкоголь в выбранном магазине и привезет чек. Стоимость покупок нужно оплатить <u>дополнительно</u> к плате за услугу.",
        "en": "📝 <b>Attention!</b> Driver will buy alcohol at selected shop and bring receipt. Purchase cost must be paid <u>additionally</u> to service fee."
    },

    "alcohol_service_description": {
        "pl": "🛒 <b>Usługa zakupu i dostawy alkoholu</b>\n\nKierowca kupi alkohol zgodnie z Twoją listą i dostawi pod wskazany adres.",
        "ru": "🛒 <b>Услуга покупки и доставки алкоголя</b>\n\nВодитель купит алкоголь согласно вашему списку и доставит по указанному адресу.",
        "en": "🛒 <b>Alcohol purchase and delivery service</b>\n\nDriver will buy alcohol according to your list and deliver to specified address."
    },

    "alcohol_order_waiting": {
        "pl": "🕒 <b>Zamówienie oczekuje na akceptację przez kierowcę</b>\n\nPo akceptacji otrzymasz:\n- Dane kierowcy i pojazdu\n- Szacowany czas realizacji",
        "ru": "🕒 <b>Заказ ожидает принятия водителем</b>\n\nПосле подтверждения вы получите:\n- Данные водителя и автомобиля\n- Примерное время выполнения",
        "en": "🕒 <b>Order awaiting driver acceptance</b>\n\nAfter confirmation you will receive:\n- Driver and vehicle details\n- Estimated completion time"
    },

    "back_to_menu": {
        "pl": "↩️ Wróć do menu",
        "ru": "↩️ Назад в меню",
        "en": "↩️ Back to menu"
    },

    "route_error": {
        "pl": "❌ Błąd trasy. Sprawdź adresy.",
        "ru": "❌ Ошибка маршрута. Проверьте адреса.",
        "en": "❌ Route error. Check addresses."
    },

    "yes": {
        "pl": "✔ Tak",
        "ru": "✔ Да",
        "en": "✔ Yes"
    },

    "no": {
        "pl": "✖ Nie",
        "ru": "✖ Нет",
        "en": "✖ No"
    },

    "order_error": {
        "pl": "❌ <b>Błąd podczas tworzenia zamówienia</b>",
        "ru": "❌ <b>Ошибка при создании заказа</b>",
        "en": "❌ <b>Error creating order</b>"
    },

    "start": {
        "pl": "👋 Witaj! Wybierz usługę:",
        "ru": "👋 Добро пожаловать! Выберите услугу:",
        "en": "👋 Hello! Choose service:"
    },

    # Ошибки
    "address_not_found": {
        "pl": "❌ Nie mogę znaleźć tego adresu. Spróbuj ponownie:",
        "ru": "❌ Не могу найти этот адрес. Попробуйте еще раз:",
        "en": "❌ Cannot find this address. Please try again:"
    },

    "invalid_location": {
        "pl": "❌ Nieprawidłowa lokalizacja. Spróbuj ponownie:",
        "ru": "❌ Неверная локация. Попробуйте еще раз:",
        "en": "❌ Invalid location. Please try again:"
    },

    "invalid_passengers_count": {
        "pl": "❌ Nieprawidłowa liczba pasażerów. Wybierz od 1 do 4:",
        "ru": "❌ Неверное количество пассажиров. Выберите от 1 до 4:",
        "en": "❌ Invalid number of passengers. Choose from 1 to 4:"
    },

    "validation_error": {
        "pl": "❌ Błąd walidacji: {error}",
        "ru": "❌ Ошибка валидации: {error}",
        "en": "❌ Validation error: {error}"
    },

    "not_found_error": {
        "pl": "❌ Nie znaleziono.",
        "ru": "❌ Не найдено.",
        "en": "❌ Not found."
    },

    "service_error": {
        "pl": "❌ Błąd serwisu. Spróbuj ponownie później.",
        "ru": "❌ Ошибка сервиса. Попробуйте позже.",
        "en": "❌ Service error. Please try again later."
    },

    "unexpected_error": {
        "pl": "❌ Wystąpił nieoczekiwany błąd. Spróbuj ponownie.",
        "ru": "❌ Произошла неожиданная ошибка. Попробуйте еще раз.",
        "en": "❌ An unexpected error occurred. Please try again."
    },

    # Настройки
    "settings_menu": {
        "pl": "⚙️ <b>Ustawienia</b>\n\nWybierz opcję:",
        "ru": "⚙️ <b>Настройки</b>\n\nВыберите опцию:",
        "en": "⚙️ <b>Settings</b>\n\nChoose an option:"
    },

    "select_language": {
        "pl": "🌐 Wybierz język:",
        "ru": "🌐 Выберите язык:",
        "en": "🌐 Select language:"
    },

    "language_changed": {
        "pl": "✅ Język został zmieniony na polski.",
        "ru": "✅ Язык изменен на русский.",
        "en": "✅ Language changed to English."
    },

    # История поездок
    "rides_history": {
        "pl": "📋 <b>Historia Twoich przejazdów:</b>\n\n🚧 Ta funkcja będzie wkrótce dostępna.",
        "ru": "📋 <b>История ваших поездок:</b>\n\n🚧 Эта функция скоро будет доступна.",
        "en": "📋 <b>Your ride history:</b>\n\n🚧 This feature will be available soon."
    },

    # Для водителей
    "new_order_notification": {
        "pl": "🚖 <b>Nowe zamówienie!</b>\n\n📍 <b>Odbiór:</b> {pickup}\n📍 <b>Cel:</b> {destination}\n💰 <b>Cena:</b> {price} PLN\n👥 <b>Pasażerów:</b> {passengers}\n📏 <b>Dystans:</b> {distance} km\n\n⏰ Czas na odpowiedź: 60 sekund",
        "ru": "🚖 <b>Новый заказ!</b>\n\n📍 <b>Подача:</b> {pickup}\n📍 <b>Место назначения:</b> {destination}\n💰 <b>Цена:</b> {price} PLN\n👥 <b>Пассажиров:</b> {passengers}\n📏 <b>Расстояние:</b> {distance} км\n\n⏰ Время на ответ: 60 секунд",
        "en": "🚖 <b>New order!</b>\n\n📍 <b>Pickup:</b> {pickup}\n📍 <b>Destination:</b> {destination}\n💰 <b>Price:</b> {price} PLN\n👥 <b>Passengers:</b> {passengers}\n📏 <b>Distance:</b> {distance} km\n\n⏰ Response time: 60 seconds"
    }
}


def get_text(key: str, language: Language = Language.PL, **kwargs) -> str:
    """Получить переведенный текст"""
    try:
        if key not in TRANSLATIONS:
            return f"[MISSING: {key}]"

        if language.value not in TRANSLATIONS[key]:
            # Fallback на польский
            language = Language.PL

        text = TRANSLATIONS[key][language.value]

        # Подстановка параметров
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError as e:
                return f"[FORMAT ERROR: {key}, missing {e}]"

        return text

    except Exception:
        return f"[ERROR: {key}]"