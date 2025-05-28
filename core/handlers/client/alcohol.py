"""
Обработчик заказов алкоголя (покупка и доставка из магазинов)
ИСПРАВЛЕНО: Фиксированная цена 20 zł вместо 71.50 zł
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.states import AlcoholOrderState
from core.services.user_service import UserService
from core.models import User, Ride, RideStatus
from core.database import get_session

logger = logging.getLogger(__name__)
router = Router()

print("🧪 [ALCOHOL] Testing service import at module load...")
try:
    from core.services.driver_notification import driver_notification_service as test_service
    print(f"✅ [ALCOHOL] Service import successful at module load")
    print(f"📊 [ALCOHOL] Service methods: {dir(test_service)}")
    print(f"📊 [ALCOHOL] Pending orders type: {type(test_service.pending_orders)}")
except Exception as import_error:
    print(f"❌ [ALCOHOL] Service import failed at module load: {import_error}")
    import traceback
    traceback.print_exc()


async def test_service_directly():
    """Тест сервиса напрямую"""
    print(f"🧪 [ALCOHOL] Testing service directly...")
    try:
        from core.services.driver_notification import driver_notification_service

        test_order_id = 9999
        test_data = {'test': 'data'}

        print(f"📦 [ALCOHOL] Adding test order {test_order_id} directly to service...")
        driver_notification_service.pending_orders[test_order_id] = test_data

        print(f"📊 [ALCOHOL] Pending orders after direct add: {list(driver_notification_service.pending_orders.keys())}")

        if test_order_id in driver_notification_service.pending_orders:
            print(f"✅ [ALCOHOL] Direct add to service works!")
        else:
            print(f"❌ [ALCOHOL] Direct add to service failed!")

        # Очистка
        driver_notification_service.pending_orders.pop(test_order_id, None)

    except Exception as e:
        print(f"❌ [ALCOHOL] Direct service test failed: {e}")


# Функции локализации
def get_localization(lang: str, key: str) -> str:
    """Функция локализации с поддержкой всех языков"""
    translations = {
        "pl": {
            "start": "👋 Witaj! Wybierz usługę:",
            "enter_shopping_list": "🛒 Wprowadź listę zakupów (np. 1x Żubr 0.5L, 2x Żywiec, 1x Vodka):",
            "enter_budget": "💰 Podaj maksymalny budżet na zakupy (w zł):",
            "invalid_budget": "❌ Nieprawidłowy budżet! Wprowadź liczbę:",
            "budget_too_low": "❌ Minimalna kwota zakupów to 20 zł",
            "confirm_age": "🔞 Czy masz ukończone 18 lat?",
            "age_warning": "🚫 Dostawa alkoholu możliwa tylko dla osób pełnoletnich!",
            "enter_alcohol_address": "📍 Podaj adres dostawy:",
            "alcohol_shop_tariff_info": "🚚 <b>Dostawa alkoholu:</b>\n\n• Stała opłata: 20 zł\n• Dostawa w ciągu 60 minut\n• Płatność <u>wyłącznie gotówką</u>",
            "alcohol_cash_only": "⚠️ <b>Uwaga!</b> Przy dostawie alkoholu możliwa jest <u>wyłącznie płatność gotówką</u>!",
            "alcohol_shop_receipt_info": "📝 <b>Uwaga!</b> Kierowca przywiezie paragon za alkohol, który należy opłacić <u>dodatkowo</u> do kosztów dostawy.",
            "back_to_menu": "↩️ Wróć do menu",
            "route_error": "❌ Błąd trasy. Sprawdź adresy.",
            "yes": "✔ Tak",
            "no": "✖ Nie",
            "alcohol_service_description": "🛒 <b>Usługa zakupu i dostawy alkoholu</b>\n\nKierowca kupi alkohol zgodnie z Twoją listą i dostawi pod wskazany adres.",
            "alcohol_order_waiting": "🕒 <b>Zamówienie oczekuje na akceptację przez kierowcę</b>\n\nPo akceptacji otrzymasz:\n- Dane kierowcy i pojazdu\n- Szacowany czas realizacji",
            "order_cancelled": "❌ <b>Zamówienie anulowane</b>",
            "order_error": "❌ <b>Błąd podczas tworzenia zamówienia</b>",
        },
        "ru": {
            "start": "👋 Добро пожаловать! Выберите услугу:",
            "enter_shopping_list": "🛒 Введите список покупок (напр. 1x Пиво 0.5Л, 2x Водка, 1x Вино):",
            "enter_budget": "💰 Укажите максимальный бюджет на покупки (в zł):",
            "invalid_budget": "❌ Неверный бюджет! Введите число:",
            "budget_too_low": "❌ Минимальная сумма покупок 20 zł",
            "confirm_age": "🔞 Вам есть 18 лет?",
            "age_warning": "🚫 Доставка алкоголя только для совершеннолетних!",
            "enter_alcohol_address": "📍 Укажите адрес доставки:",
            "alcohol_shop_tariff_info": "🚚 <b>Доставка алкоголя:</b>\n\n• Фиксированная плата: 20 zł\n• Доставка в течение 60 минут\n• Оплата <u>только наличными</u>",
            "alcohol_cash_only": "⚠️ <b>Внимание!</b> При доставке алкоголя возможна <u>только оплата наличными</u>!",
            "alcohol_shop_receipt_info": "📝 <b>Внимание!</b> Водитель привезет чек за алкоголь, который нужно оплатить <u>дополнительно</u> к стоимости доставки.",
            "back_to_menu": "↩️ Назад в меню",
            "route_error": "❌ Ошибка маршрута. Проверьте адреса.",
            "yes": "✔ Да",
            "no": "✖ Нет",
            "alcohol_service_description": "🛒 <b>Услуга покупки и доставки алкоголя</b>\n\nВодитель купит алкоголь согласно вашему списку и доставит по указанному адресу.",
            "alcohol_order_waiting": "🕒 <b>Заказ ожидает принятия водителем</b>\n\nПосле подтверждения вы получите:\n- Данные водителя и автомобиля\n- Примерное время выполнения",
            "order_cancelled": "❌ <b>Заказ отменен</b>",
            "order_error": "❌ <b>Ошибка при создании заказа</b>",
        },
        "en": {
            "start": "👋 Hello! Choose service:",
            "enter_shopping_list": "🛒 Enter shopping list (e.g. 1x Beer 0.5L, 2x Vodka, 1x Wine):",
            "enter_budget": "💰 Enter maximum budget for purchases (in zł):",
            "invalid_budget": "❌ Invalid budget! Enter a number:",
            "budget_too_low": "❌ Minimum purchase amount is 20 zł",
            "confirm_age": "🔞 Are you 18+ years old?",
            "age_warning": "🚫 Alcohol delivery only for adults!",
            "enter_alcohol_address": "📍 Enter delivery address:",
            "alcohol_shop_tariff_info": "🚚 <b>Alcohol delivery:</b>\n\n• Fixed fee: 20 zł\n• Delivery within 60 minutes\n• Payment <u>cash only</u>",
            "alcohol_cash_only": "⚠️ <b>Attention!</b> For alcohol delivery <u>only cash payment</u> is possible!",
            "alcohol_shop_receipt_info": "📝 <b>Attention!</b> Driver will bring receipt for alcohol that must be paid <u>additionally</u> to delivery cost.",
            "back_to_menu": "↩️ Back to menu",
            "route_error": "❌ Route error. Check addresses.",
            "yes": "✔ Yes",
            "no": "✖ No",
            "alcohol_service_description": "🛒 <b>Alcohol purchase and delivery service</b>\n\nDriver will buy alcohol according to your list and deliver to specified address.",
            "alcohol_order_waiting": "🕒 <b>Order awaiting driver acceptance</b>\n\nAfter confirmation you will receive:\n- Driver and vehicle details\n- Estimated completion time",
            "order_cancelled": "❌ <b>Order cancelled</b>",
            "order_error": "❌ <b>Error creating order</b>",
        }
    }
    return translations.get(lang, {}).get(key, key)


async def get_user_language(telegram_id: int) -> str:
    """Получить язык пользователя"""
    try:
        user_service = UserService()
        user = await user_service.get_user_by_telegram_id(telegram_id)
        return user.language if user and user.language else "pl"
    except Exception:
        return "pl"


# Клавиатуры
def confirm_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_localization(lang, "yes"), callback_data="confirm_yes")
    builder.button(text=get_localization(lang, "no"), callback_data="confirm_no")
    return builder.as_markup()


def back_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_localization(lang, "back_to_menu"), callback_data="back_to_menu")
    return builder.as_markup()


# Функции расчета
def calculate_distance(origin: str, destination: str) -> float:
    """Примерный расчет расстояния"""
    # TODO: Интегрировать с Google Maps API
    return 5.0


def calculate_alcohol_delivery_price(distance: float) -> float:
    """ИСПРАВЛЕНО: Фиксированная цена 20 zł для алкоголя"""
    print(f"💰 [PRICING] calculate_alcohol_delivery_price called with distance: {distance}")
    print(f"💰 [PRICING] Returning fixed price: 20.0 zł")
    return 20.0  # ФИКСИРОВАННАЯ ЦЕНА 20 zł


async def save_alcohol_order(user_id: int, order_data: dict) -> int:
    """Сохранить заказ алкоголя"""
    try:
        async with get_session() as session:
            # Используем модель Ride как основу для заказа
            ride = Ride(
                client_id=user_id,
                user_id=user_id,  # Для совместимости
                pickup_address="Alcohol Shop Delivery",
                pickup_lat=53.4285,  # Координаты Щецина
                pickup_lng=14.5528,
                destination_address=order_data['address'],
                destination_lat=53.4285,  # Примерные координаты
                destination_lng=14.5528,
                distance_km=order_data.get('distance', 5.0),
                estimated_price=order_data['price'],
                price=order_data['price'],  # Для совместимости
                status=RideStatus.PENDING,
                order_type="alcohol_delivery",
                products=order_data['products'],
                budget=order_data['budget'],
                payment_method="cash",
                notes=f"ALCOHOL DELIVERY - Products: {order_data['products']}, Budget: {order_data['budget']} zł"
            )

            session.add(ride)
            await session.commit()
            await session.refresh(ride)

            logger.info(f"Alcohol order saved: {ride.id}")
            return ride.id

    except Exception as e:
        logger.error(f"Error saving alcohol order: {e}")
        return 1  # Fallback ID


async def notify_driver_simple(order_id: int, order_data: dict):
    """Уведомление водителей с подробной отладкой"""
    print(f"🚚 [NOTIFY] notify_driver_simple called")
    print(f"   Order ID: {order_id}")
    print(f"   Order data: {order_data}")

    try:
        print(f"📦 [NOTIFY] Importing driver_notification_service...")
        from core.services.driver_notification import driver_notification_service
        print(f"✅ [NOTIFY] Service imported successfully")

        # Исправляем данные заказа
        order_data_fixed = {
            'order_type': 'alcohol_delivery',
            'products': order_data.get('products', 'N/A'),
            'budget': order_data.get('budget', 'N/A'),
            'address': order_data.get('address', 'N/A'),
            'distance': order_data.get('distance', 5.0),
            'price': order_data.get('price', 20),  # ФИКСИРОВАННАЯ ЦЕНА
            'client_id': order_data.get('client_id'),
            'user_id': order_data.get('user_id')
        }

        print(f"📋 [NOTIFY] Fixed order data: {order_data_fixed}")
        print(f"📢 [NOTIFY] Calling service.notify_all_drivers...")

        await driver_notification_service.notify_all_drivers(order_id, order_data_fixed)

        print(f"✅ [NOTIFY] notify_all_drivers completed")

        # Проверяем результат
        pending = list(driver_notification_service.pending_orders.keys())
        print(f"📊 [NOTIFY] Pending orders after notify_all_drivers: {pending}")

        if order_id in driver_notification_service.pending_orders:
            print(f"✅ [NOTIFY] SUCCESS: Order {order_id} is now in pending_orders")
        else:
            print(f"❌ [NOTIFY] FAILURE: Order {order_id} not in pending_orders")
            print(f"❌ [NOTIFY] Service may have failed to add the order")

        logger.info(f"Multiple drivers notified about alcohol order {order_id}")

    except ImportError as import_error:
        print(f"❌ [NOTIFY] Import error: {import_error}")
        print(f"❌ [NOTIFY] Using fallback notification method...")

        # Fallback к старому методу
        try:
            from core.bot_instance import Bots
            from aiogram.utils.keyboard import InlineKeyboardBuilder

            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Przyjmij", callback_data=f"accept_{order_id}")
            builder.button(text="❌ Odrzuć", callback_data=f"reject_{order_id}")

            text = (
                "🛒 <b>ZAKUP I DOSTAWA ALKOHOLU (FALLBACK)</b>\n\n"
                f"📝 <b>Lista zakupów:</b>\n{order_data['products']}\n\n"
                f"💰 <b>Budżet klienta:</b> {order_data['budget']} zł\n"
                f"📍 <b>Dostawa na:</b> {order_data['address']}\n"
                f"📏 <b>Odległość:</b> ~{order_data.get('distance', 5):.1f} km\n"
                f"💵 <b>Twoja opłata:</b> 20 zł\n\n"  # ФИКСИРОВАННАЯ ЦЕНА
                f"🆔 <b>Заказ #{order_id}</b>"
            )

            # Отправляем всем водителям из Config
            from config import Config
            for driver_id in Config.DRIVER_IDS:
                try:
                    await Bots.driver.send_message(
                        chat_id=int(driver_id),
                        text="🔊🔊🔊 NOWE ZAMÓWIENIE (FALLBACK)! 🔊🔊🔊",
                        disable_notification=False
                    )

                    await asyncio.sleep(0.5)

                    await Bots.driver.send_message(
                        chat_id=int(driver_id),
                        text=text,
                        reply_markup=builder.as_markup(),
                        parse_mode="HTML",
                        disable_notification=False
                    )
                    print(f"📨 [NOTIFY] Fallback notification sent to driver {driver_id}")

                except Exception as driver_error:
                    print(f"❌ [NOTIFY] Error sending to driver {driver_id}: {driver_error}")

            print(f"⚠️ [NOTIFY] Fallback notifications sent, but order won't be in pending_orders")
            print(f"⚠️ [NOTIFY] Handlers will show 'order not found' - this is expected for fallback")

        except Exception as fallback_error:
            print(f"💥 [NOTIFY] Both main and fallback methods failed: {fallback_error}")

    except Exception as e:
        print(f"💥 [NOTIFY] Unexpected error in notify_driver_simple: {e}")
        import traceback
        traceback.print_exc()


# Обработчики callback-ов от главного меню
@router.callback_query(F.data == "confirm_yes", AlcoholOrderState.waiting_products)
async def handle_confirm_yes_start_order(callback: CallbackQuery, state: FSMContext):
    """Обработка подтверждения начала заказа алкоголя"""
    lang = await get_user_language(callback.from_user.id)

    await callback.message.answer(
        text=get_localization(lang, "enter_shopping_list"),
        reply_markup=back_keyboard(lang)
    )
    await state.set_state(AlcoholOrderState.waiting_budget)


@router.callback_query(F.data == "confirm_yes", AlcoholOrderState.confirmation)
async def handle_confirm_yes_final(callback: CallbackQuery, state: FSMContext):
    """Обработка финального подтверждения заказа"""
    await confirm_alcohol_order(callback, state)


@router.callback_query(F.data == "confirm_no")
async def handle_confirm_no_from_menu(callback: CallbackQuery, state: FSMContext):
    """Обработка отмены из главного меню"""
    await cancel_order(callback, state)


@router.callback_query(F.data == "menu_alcohol")
async def start_alcohol_order(callback: CallbackQuery, state: FSMContext):
    """Начало заказа алкоголя"""
    lang = await get_user_language(callback.from_user.id)

    await callback.message.edit_text(
        text=get_localization(lang, "alcohol_service_description"),
        parse_mode="HTML",
        reply_markup=confirm_keyboard(lang)
    )
    await state.set_state(AlcoholOrderState.waiting_products)


@router.message(AlcoholOrderState.waiting_budget)
async def process_shopping_list(message: Message, state: FSMContext):
    """Обработка списка покупок"""
    lang = await get_user_language(message.from_user.id)

    if message.text == get_localization(lang, "back_to_menu"):
        await state.clear()
        await return_to_main_menu(message, lang)
        return

    await state.update_data(products=message.text)
    await message.answer(
        text=get_localization(lang, "enter_budget"),
        reply_markup=back_keyboard(lang)
    )
    await state.set_state(AlcoholOrderState.waiting_age)


@router.message(AlcoholOrderState.waiting_age)
async def process_budget(message: Message, state: FSMContext):
    """Обработка бюджета"""
    lang = await get_user_language(message.from_user.id)

    if message.text == get_localization(lang, "back_to_menu"):
        await state.clear()
        await return_to_main_menu(message, lang)
        return

    try:
        budget = float(message.text)
        if budget < 20:
            await message.answer(get_localization(lang, "budget_too_low"))
            return

        await state.update_data(budget=budget)
        await message.answer(
            text=get_localization(lang, "confirm_age"),
            reply_markup=confirm_keyboard(lang)
        )
        await state.set_state(AlcoholOrderState.waiting_address)

    except ValueError:
        await message.answer(get_localization(lang, "invalid_budget"))


@router.callback_query(AlcoholOrderState.waiting_address, F.data.startswith("confirm_"))
async def process_age_confirmation(callback: CallbackQuery, state: FSMContext):
    """Подтверждение возраста"""
    lang = await get_user_language(callback.from_user.id)
    is_adult = callback.data.split("_")[1] == "yes"

    if not is_adult:
        # Если несовершеннолетний, возвращаем в главное меню
        await state.clear()

        # Сначала редактируем текущее сообщение
        await callback.message.edit_text(
            text=get_localization(lang, "age_warning"),
            parse_mode="HTML"
        )

        # Затем отправляем новое сообщение с главным меню
        await return_to_main_menu_callback(callback, lang)
        return

    await callback.message.answer(
        text=get_localization(lang, "alcohol_shop_tariff_info"),
        parse_mode="HTML"
    )

    await callback.message.answer(
        text=get_localization(lang, "enter_alcohol_address"),
        reply_markup=back_keyboard(lang)
    )
    await state.set_state(AlcoholOrderState.confirmation)


@router.message(AlcoholOrderState.confirmation)
async def process_delivery_address(message: Message, state: FSMContext):
    """ИСПРАВЛЕНО: Обработка адреса доставки с фиксированной ценой"""
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()

    if message.text == get_localization(lang, "back_to_menu"):
        await state.clear()
        await return_to_main_menu(message, lang)
        return

    try:
        distance = calculate_distance("Plac Żołnierza, Szczecin", message.text)
        price = calculate_alcohol_delivery_price(distance)  # Всегда 20 zł

        print(f"💰 [ADDRESS] Distance: {distance}, Price: {price}")

        await state.update_data(address=message.text, distance=distance, price=price)

        await message.answer(
            text=get_localization(lang, "alcohol_cash_only") + "\n\n" +
                 get_localization(lang, "alcohol_shop_receipt_info"),
            parse_mode="HTML"
        )

        # ИСПРАВЛЕНО: Локализованные строки с фиксированной ценой
        if lang == "pl":
            order_text = (
                f"🍾 <b>Dostawa alkoholu</b>\n\n"
                f"📋 <b>Lista zakupów:</b>\n<i>{data['products']}</i>\n\n"
                f"💰 <b>Budżet na zakupy:</b> {data['budget']} zł\n"
                f"🏠 <b>Adres dostawy:</b>\n{message.text}\n"
                f"📏 <b>Odległość:</b> ~{distance:.1f} km\n\n"
                f"💵 <b>Opłata za dostawę:</b> 20 zł\n"  # ФИКСИРОВАННАЯ ЦЕНА
                f"💵 <b>+ koszt zakupów</b> (do {data['budget']} zł)\n\n"
                f"💰 <b>Płatność:</b> gotówka\n"
                f"🕒 <b>Czas realizacji:</b> 30-45 minut"
            )
        elif lang == "ru":
            order_text = (
                f"🍾 <b>Доставка алкоголя</b>\n\n"
                f"📋 <b>Список покупок:</b>\n<i>{data['products']}</i>\n\n"
                f"💰 <b>Бюджет на покупки:</b> {data['budget']} zł\n"
                f"🏠 <b>Адрес доставки:</b>\n{message.text}\n"
                f"📏 <b>Расстояние:</b> ~{distance:.1f} км\n\n"
                f"💵 <b>Плата за доставку:</b> 20 zł\n"  # ФИКСИРОВАННАЯ ЦЕНА
                f"💵 <b>+ стоимость покупок</b> (до {data['budget']} zł)\n\n"
                f"💰 <b>Оплата:</b> наличные\n"
                f"🕒 <b>Время выполнения:</b> 30-45 минут"
            )
        else:  # en
            order_text = (
                f"🍾 <b>Alcohol delivery</b>\n\n"
                f"📋 <b>Shopping list:</b>\n<i>{data['products']}</i>\n\n"
                f"💰 <b>Shopping budget:</b> {data['budget']} zł\n"
                f"🏠 <b>Delivery address:</b>\n{message.text}\n"
                f"📏 <b>Distance:</b> ~{distance:.1f} km\n\n"
                f"💵 <b>Delivery fee:</b> 20 zł\n"  # ФИКСИРОВАННАЯ ЦЕНА
                f"💵 <b>+ purchase cost</b> (up to {data['budget']} zł)\n\n"
                f"💰 <b>Payment:</b> cash\n"
                f"🕒 <b>Completion time:</b> 30-45 minutes"
            )

        await message.answer(
            text=order_text,
            parse_mode="HTML",
            reply_markup=confirm_keyboard(lang)
        )

    except Exception as e:
        logger.error(f"Error processing address: {e}")
        await message.answer(get_localization(lang, "route_error"))


@router.callback_query(F.data.startswith("confirm_"), AlcoholOrderState.confirmation)
async def confirm_alcohol_order(callback: CallbackQuery, state: FSMContext):
    """Подтверждение заказа с подробной отладкой"""
    lang = await get_user_language(callback.from_user.id)
    action = callback.data.split("_")[1]

    print(f"🍷 [ALCOHOL] confirm_alcohol_order called")
    print(f"   User: {callback.from_user.id}")
    print(f"   Action: {action}")

    if action == "yes":
        data = await state.get_data()
        print(f"📋 [ALCOHOL] Order data from state: {data}")

        try:
            print(f"💾 [ALCOHOL] Saving order to database...")
            order_id = await save_alcohol_order(callback.from_user.id, data)
            print(f"✅ [ALCOHOL] Order saved with ID: {order_id}")

            # Добавляем client_id в данные для уведомления
            data['client_id'] = callback.from_user.id
            data['user_id'] = callback.from_user.id

            print(f"📋 [ALCOHOL] Enhanced order data: {data}")
            print(f"📢 [ALCOHOL] Calling notify_driver_simple...")

            await notify_driver_simple(order_id, data)
            print(f"✅ [ALCOHOL] notify_driver_simple completed")

            # Проверяем попал ли заказ в сервис
            try:
                from core.services.driver_notification import driver_notification_service
                pending = list(driver_notification_service.pending_orders.keys())
                print(f"📊 [ALCOHOL] Pending orders after notify: {pending}")

                if order_id in driver_notification_service.pending_orders:
                    print(f"✅ [ALCOHOL] Order {order_id} successfully added to pending_orders")
                else:
                    print(f"❌ [ALCOHOL] Order {order_id} NOT found in pending_orders!")
                    print(f"❌ [ALCOHOL] This is why handlers can't find the order!")

            except Exception as check_error:
                print(f"❌ [ALCOHOL] Error checking pending orders: {check_error}")

            await callback.message.edit_text(
                text=get_localization(lang, "alcohol_order_waiting"),
                parse_mode="HTML"
            )

        except Exception as e:
            print(f"💥 [ALCOHOL] Error confirming order: {e}")
            import traceback
            traceback.print_exc()
            await callback.message.edit_text(
                text=get_localization(lang, "order_error"),
                parse_mode="HTML"
            )
    else:
        print(f"❌ [ALCOHOL] Order cancelled by user")
        await callback.message.edit_text(
            text=get_localization(lang, "order_cancelled"),
            parse_mode="HTML"
        )

    await state.clear()
    print(f"🏁 [ALCOHOL] confirm_alcohol_order completed")


@router.callback_query(F.data == "confirm_no")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    """Отмена заказа"""
    lang = await get_user_language(callback.from_user.id)
    await state.clear()

    # Сначала редактируем текущее сообщение без клавиатуры
    await callback.message.edit_text(
        text=get_localization(lang, "order_cancelled"),
        parse_mode="HTML"
    )

    # Затем отправляем новое сообщение с главным меню
    await return_to_main_menu_callback(callback, lang)


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    lang = await get_user_language(callback.from_user.id)

    # Сначала редактируем текущее сообщение без клавиатуры
    await callback.message.edit_text(
        text=get_localization(lang, "start")
    )

    # Затем отправляем новое сообщение с главным меню
    await return_to_main_menu_callback(callback, lang)


async def return_to_main_menu(message: Message, lang: str):
    """Возврат в главное меню для Message"""
    from core.keyboards import get_main_menu_keyboard
    from core.models import UserRole

    keyboard = get_main_menu_keyboard(lang, UserRole.CLIENT)
    await message.answer(
        text=get_localization(lang, "start"),
        reply_markup=keyboard
    )


async def return_to_main_menu_callback(callback: CallbackQuery, lang: str):
    """Возврат в главное меню для CallbackQuery"""
    from core.keyboards import get_main_menu_keyboard
    from core.models import UserRole

    keyboard = get_main_menu_keyboard(lang, UserRole.CLIENT)
    await callback.message.answer(
        text=get_localization(lang, "start"),
        reply_markup=keyboard
    )