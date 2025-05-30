"""
Обработчики для управления поездкой клиентом - С СИСТЕМОЙ ОЖИДАНИЯ
"""
import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message, Location
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.models import Session, Ride as Order
from core.bot_instance import Bots
from core.services.maps_service import MapsService, Location as MapLocation
from core.services.price_calculator import PriceCalculatorService
from core.keyboards import (
    get_client_ride_keyboard,
    get_location_keyboard,
    get_passengers_keyboard,
    get_ride_confirmation_keyboard,
    get_main_menu_keyboard
)
from core.states import ClientStates
from core.utils.localization import get_text, Language
from core.models import UserRole

logger = logging.getLogger(__name__)
taxi_router = Router()
maps_service = MapsService()


async def get_user_language_simple(user_id: int) -> str:
    """Простая функция получения языка пользователя"""
    try:
        from core.services.user_service import UserService
        user_service = UserService()
        user = await user_service.get_user_by_telegram_id(user_id)
        return user.language if user and user.language else "pl"
    except Exception:
        return "pl"


async def get_user_language(telegram_id: int) -> Language:
    """Получить язык пользователя"""
    try:
        from core.services.user_service import UserService
        user_service = UserService()
        user = await user_service.get_user_by_telegram_id(telegram_id)
        if user and user.language in ['en', 'pl', 'ru']:
            return Language(user.language)
        return Language.PL
    except Exception as e:
        logger.error(f"Error getting user language: {e}")
        return Language.PL


# ===================================================================
# ОБРАБОТЧИКИ ПРОЦЕССА ЗАКАЗА ТАКСИ
# ===================================================================

@taxi_router.message(F.location, StateFilter(ClientStates.WAITING_PICKUP_LOCATION))
async def handle_pickup_location(message: Message, state: FSMContext):
    """Обработка локации подачи"""
    try:
        # Получаем адрес по координатам
        address = await maps_service.reverse_geocode(
            message.location.latitude,
            message.location.longitude
        )

        pickup_location = MapLocation(
            latitude=message.location.latitude,
            longitude=message.location.longitude,
            address=address
        )

        # Сохраняем в состояние
        await state.update_data(pickup_location=pickup_location)

        language = await get_user_language(message.from_user.id)

        await message.answer(
            f"✅ <b>Miejsce odbioru:</b>\n{address}\n\n"
            f"📍 Teraz wyślij lokalizację docelową lub wpisz adres:",
            parse_mode="HTML",
            reply_markup=get_location_keyboard(language.value)
        )

        await state.set_state(ClientStates.WAITING_DESTINATION_LOCATION)

    except Exception as e:
        logger.error(f"Error handling pickup location: {e}")
        await message.answer("❌ Błąd podczas przetwarzania lokalizacji")


@taxi_router.message(F.location, StateFilter(ClientStates.WAITING_DESTINATION_LOCATION))
async def handle_destination_location(message: Message, state: FSMContext):
    """Обработка локации назначения"""
    try:
        # Получаем адрес по координатам
        address = await maps_service.reverse_geocode(
            message.location.latitude,
            message.location.longitude
        )

        destination_location = MapLocation(
            latitude=message.location.latitude,
            longitude=message.location.longitude,
            address=address
        )

        # Сохраняем в состояние
        await state.update_data(destination_location=destination_location)

        language = await get_user_language(message.from_user.id)

        await message.answer(
            f"✅ <b>Miejsce docelowe:</b>\n{address}\n\n"
            f"👥 Wybierz liczbę pasażerów:",
            parse_mode="HTML",
            reply_markup=get_passengers_keyboard(language.value)
        )

        await state.set_state(ClientStates.WAITING_PASSENGERS_COUNT)

    except Exception as e:
        logger.error(f"Error handling destination location: {e}")
        await message.answer("❌ Błąd podczas przetwarzania lokalizacji")


@taxi_router.message(F.text.regexp(r'^[1-4]$'), StateFilter(ClientStates.WAITING_PASSENGERS_COUNT))
async def handle_passengers_count(message: Message, state: FSMContext):
    """Обработка количества пассажиров"""
    try:
        passengers = int(message.text)
        await state.update_data(passengers_count=passengers)

        # Получаем данные для подтверждения
        data = await state.get_data()
        pickup = data['pickup_location']
        destination = data['destination_location']

        # Рассчитываем примерную стоимость
        distance = pickup.distance_to(destination)
        price_service = PriceCalculatorService()
        estimated_price = price_service.calculate_price(distance)

        language = await get_user_language(message.from_user.id)

        await message.answer(
            f"📋 <b>Podsumowanie zamówienia:</b>\n\n"
            f"📍 <b>Odbiór:</b> {pickup.address}\n"
            f"📍 <b>Cel:</b> {destination.address}\n"
            f"👥 <b>Pasażerów:</b> {passengers}\n"
            f"📏 <b>Dystans:</b> {distance:.1f} km\n"
            f"💵 <b>Koszt:</b> {estimated_price} zł\n"
            f"⏱️ <b>Szacowany czas:</b> {int(distance * 2.5)} min\n\n"
            f"✅ Potwierdź zamówienie:",
            reply_markup=get_ride_confirmation_keyboard(language.value),
            parse_mode="HTML"
        )

        await state.set_state(ClientStates.WAITING_RIDE_CONFIRMATION)

    except Exception as e:
        logger.error(f"Error handling passengers count: {e}")
        await message.answer("❌ Błąd podczas przetwarzania danych")


@taxi_router.callback_query(F.data == "confirm_ride")
async def confirm_ride(callback: CallbackQuery, state: FSMContext):
    """Подтверждение заказа такси клиентом"""
    try:
        # Получаем данные из состояния
        data = await state.get_data()

        if not all(key in data for key in ['pickup_location', 'destination_location', 'passengers_count']):
            await callback.answer("❌ Dane zamówienia są niekompletne")
            return

        # Создаем заказ в базе данных
        with Session() as session:
            from core.models import Ride
            from datetime import datetime

            price_service = PriceCalculatorService()

            # Рассчитываем стоимость
            pickup_loc = data['pickup_location']
            dest_loc = data['destination_location']
            distance = pickup_loc.distance_to(dest_loc)
            estimated_price = price_service.calculate_price(distance)

            # Создаем заказ
            order = Ride(
                client_id=callback.from_user.id,
                pickup_address=pickup_loc.address,
                pickup_lat=pickup_loc.latitude,
                pickup_lng=pickup_loc.longitude,
                destination_address=dest_loc.address,
                destination_lat=dest_loc.latitude,
                destination_lng=dest_loc.longitude,
                distance_km=distance,
                estimated_price=estimated_price,
                passengers_count=data['passengers_count'],
                status="pending",
                order_type="city_ride"
            )

            session.add(order)
            session.commit()
            session.refresh(order)

            order_id = order.id

        # Отправляем заказ водителям через сервис уведомлений если доступен
        try:
            from core.services.driver_notification import driver_notification_service

            order_data = {
                'order_id': order_id,
                'client_id': callback.from_user.id,
                'pickup_address': pickup_loc.address,
                'destination_address': dest_loc.address,
                'distance_km': distance,
                'estimated_price': float(estimated_price),
                'passengers_count': data['passengers_count'],
                'order_type': 'city_ride'
            }

            await driver_notification_service.notify_all_drivers(order_id, order_data)
        except ImportError:
            # Fallback - простое уведомление водителей
            from config import Config
            from aiogram.utils.keyboard import InlineKeyboardBuilder

            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Przyjmij", callback_data=f"accept_{order_id}")
            builder.button(text="❌ Odrzuć", callback_data=f"reject_{order_id}")

            notification_text = (
                f"🚖 <b>Nowe zamówienie!</b>\n\n"
                f"📍 Z: {pickup_loc.address}\n"
                f"📍 Do: {dest_loc.address}\n"
                f"💵 Cena: {estimated_price} zł\n"
                f"👥 Pasażerów: {data['passengers_count']}\n"
                f"📏 Dystans: {distance:.1f} km"
            )

            await Bots.driver.send_message(
                chat_id=Config.DRIVER_CHAT_ID,
                text=notification_text,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )

        # Обновляем сообщение клиента
        language = await get_user_language(callback.from_user.id)

        await callback.message.edit_text(
            f"✅ <b>Zamówienie złożone!</b>\n\n"
            f"📦 <b>Numer zamówienia:</b> #{order_id}\n"
            f"📍 <b>Odbiór:</b> {pickup_loc.address}\n"
            f"📍 <b>Cel:</b> {dest_loc.address}\n"
            f"👥 <b>Pasażerów:</b> {data['passengers_count']}\n"
            f"💵 <b>Koszt:</b> {estimated_price} zł\n"
            f"📏 <b>Dystans:</b> {distance:.1f} km\n\n"
            f"⏰ Szukamy dostępnego kierowcy...",
            reply_markup=get_client_ride_keyboard(language.value, "pending"),
            parse_mode="HTML"
        )

        await callback.answer("✅ Zamówienie złożone!")
        await state.set_state(ClientStates.RIDE_IN_PROGRESS)  # Обновили состояние

    except Exception as e:
        logger.error(f"Error confirming ride: {e}")
        await callback.answer("❌ Błąd podczas składania zamówienia")


# ===================================================================
# СИСТЕМА ОЖИДАНИЯ - ОБРАБОТЧИКИ ДЛЯ КЛИЕНТА
# ===================================================================

@taxi_router.callback_query(F.data == "request_stop")
async def request_stop(callback: CallbackQuery):
    """ОБНОВЛЕННЫЙ: Запросить остановку во время поездки"""
    try:
        print(f"🛑 [CLIENT] Stop request from passenger {callback.from_user.id}")

        with Session() as session:
            order = session.query(Order).filter_by(
                client_id=callback.from_user.id,
                status="in_progress"
            ).order_by(Order.created_at.desc()).first()

            if not order or not order.driver_id:
                await callback.answer("❌ Активная поездка не найдена")
                return

            print(f"🎯 [CLIENT] Found active ride {order.id} with driver {order.driver_id}")

            # Проверяем, не активен ли уже счетчик ожидания
            try:
                from core.handlers.driver.ride_handlers import waiting_timers
                if order.id in waiting_timers:
                    await callback.answer("⏰ Licznik oczekiwania już jest aktywny")
                    return
            except ImportError:
                print("⚠️ [CLIENT] Could not import waiting_timers, continuing anyway")

            # Создаем клавиатуру для водителя
            builder = InlineKeyboardBuilder()
            builder.button(text="⏸️ Zatrzymaj i uruchom licznik", callback_data="accept_waiting")
            builder.button(text="❌ Nie mogę się zatrzymać", callback_data="decline_waiting")
            builder.adjust(1)

            # Уведомляем водителя о запросе остановки
            passenger_name = callback.from_user.first_name or f"ID {callback.from_user.id}"

            driver_message = (
                "⏸️ <b>PASAŻER PROSI O ZATRZYMANIE</b>\n\n"
                f"🚖 <b>ID podróży:</b> {order.id}\n"
                f"👤 <b>Pasażer:</b> {passenger_name}\n"
                f"📍 <b>Trasa:</b> {order.pickup_address} → {order.destination_address}\n\n"
                "⏰ <b>Taryfa oczekiwania:</b> 1 zł/minuta\n\n"
                "Wybierz działanie:"
            )

            await Bots.driver.send_message(
                chat_id=order.driver_id,
                text=driver_message,
                parse_mode="HTML",
                reply_markup=builder.as_markup()
            )

            print(f"📢 [CLIENT] Sent stop request to driver {order.driver_id}")

            # Уведомляем пассажира
            passenger_message = (
                "⏸️ <b>Prośba o zatrzymanie wysłana!</b>\n\n"
                "⏰ <b>Taryfa oczekiwania:</b> 1 zł/minuta\n\n"
                "Czekamy na odpowiedź kierowcy..."
            )

            await callback.message.edit_text(
                text=passenger_message,
                parse_mode="HTML"
            )

            await callback.answer("✅ Prośba wysłana do kierowcy")
            print(f"✅ [CLIENT] Stop request processed successfully")

    except Exception as e:
        logger.error(f"Error requesting stop: {e}")
        print(f"💥 [CLIENT] Error: {e}")
        await callback.answer("❌ Błąd podczas wysyłania prośby")


@taxi_router.callback_query(F.data == "current_location")
async def show_current_location_enhanced(callback: CallbackQuery):
    """ОБНОВЛЕННЫЙ: Показать текущее местоположение (для пассажира)"""
    try:
        print(f"📍 [CLIENT] Location request from passenger {callback.from_user.id}")

        # Находим активную поездку пассажира
        with Session() as session:
            order = session.query(Order).filter(
                Order.client_id == callback.from_user.id,
                Order.status.in_(["accepted", "driver_arrived", "in_progress"])
            ).order_by(Order.created_at.desc()).first()

            if not order or not order.driver_id:
                await callback.answer("❌ Активная поездка не найдена")
                return

            # Запрашиваем у водителя текущее местоположение
            await Bots.driver.send_message(
                chat_id=order.driver_id,
                text=(
                    "📍 <b>PASAŻER PROSI O LOKALIZACJĘ</b>\n\n"
                    "Pasażer chce poznać Twoją aktualną lokalizację.\n"
                    "Naciśnij przycisk 'Транслировать геопозицию' aby wysłać swoją lokalizację."
                ),
                parse_mode="HTML"
            )

            await callback.answer("✅ Poproszono kierowcę o lokalizację")

            await callback.message.edit_text(
                "📍 <b>Prośba o lokalizację wysłana</b>\n\n"
                "Poproszono kierowcę o przesłanie aktualnej lokalizacji.",
                parse_mode="HTML"
            )

            print(f"📍 [CLIENT] Location request sent to driver {order.driver_id}")

    except Exception as e:
        logger.error(f"Error requesting current location: {e}")
        await callback.answer("❌ Błąd podczas pobierania lokalizacji")


@taxi_router.callback_query(F.data == "ready_to_continue")
async def passenger_ready_to_continue(callback: CallbackQuery):
    """Пассажир готов продолжить поездку"""
    try:
        print(f"✅ [CLIENT] Passenger ready to continue: {callback.from_user.id}")

        # Находим активную поездку пассажира
        with Session() as session:
            order = session.query(Order).filter(
                Order.client_id == callback.from_user.id,
                Order.status == "in_progress"
            ).order_by(Order.created_at.desc()).first()

            if not order or not order.driver_id:
                await callback.answer("❌ Активная поездка не найдена")
                return

            # Уведомляем водителя
            await Bots.driver.send_message(
                chat_id=order.driver_id,
                text=(
                    "✅ <b>PASAŻER GOTOWY DO KONTYNUACJI</b>\n\n"
                    "Pasażer jest gotowy do kontynuacji podróży.\n"
                    "Możesz zakończyć oczekiwanie i kontynuować jazdę."
                ),
                parse_mode="HTML"
            )

            await callback.message.edit_text(
                "✅ <b>Kierowca został powiadomiony</b>\n\n"
                "Poinformowaliśmy kierowcę, że jesteś gotowy do kontynuacji podróży.",
                parse_mode="HTML"
            )

            await callback.answer("✅ Kierowca został powiadomiony")
            print(f"📢 [CLIENT] Notified driver {order.driver_id} that passenger is ready")

    except Exception as e:
        logger.error(f"Error notifying driver passenger ready: {e}")
        await callback.answer("❌ Błąd podczas powiadamiania kierowcy")


@taxi_router.callback_query(F.data == "check_waiting_cost")
async def check_waiting_cost_passenger(callback: CallbackQuery):
    """Пассажир проверяет стоимость ожидания"""
    try:
        print(f"📊 [CLIENT] Passenger checking waiting cost: {callback.from_user.id}")

        # Находим активную поездку пассажира
        with Session() as session:
            order = session.query(Order).filter(
                Order.client_id == callback.from_user.id,
                Order.status == "in_progress"
            ).order_by(Order.created_at.desc()).first()

            if not order:
                await callback.answer("❌ Активная поездка не найдена")
                return

            # Ищем активный счетчик для этой поездки
            try:
                from core.handlers.driver.ride_handlers import waiting_timers
                from datetime import datetime

                if order.id in waiting_timers:
                    start_time = waiting_timers[order.id]['start_time']
                    current_time = datetime.now()
                    elapsed = current_time - start_time
                    minutes = int(elapsed.total_seconds() / 60)
                    cost = max(1, minutes)  # Минимум 1 минута

                    text = (
                        f"📊 <b>AKTUALNY KOSZT OCZEKIWANIA</b>\n\n"
                        f"⏰ <b>Rozpoczęto:</b> {start_time.strftime('%H:%M:%S')}\n"
                        f"⏱️ <b>Upłynęło:</b> {minutes} min\n"
                        f"💰 <b>Koszt:</b> {cost} zł\n\n"
                        f"<i>Taryfa: 1 zł za minutę</i>"
                    )
                else:
                    text = "ℹ️ Licznik oczekiwania nie jest aktywny"

            except ImportError:
                text = "⚠️ Informacje o oczekiwaniu niedostępne"

            await callback.answer(text, show_alert=True)

    except Exception as e:
        logger.error(f"Error checking waiting cost for passenger: {e}")
        await callback.answer("❌ Błąd podczas sprawdzania kosztu")


# ===================================================================
# СТАНДАРТНЫЕ ОБРАБОТЧИКИ УПРАВЛЕНИЯ ПОЕЗДКОЙ
# ===================================================================

@taxi_router.callback_query(F.data == "cancel_ride")
async def cancel_ride_client(callback: CallbackQuery, state: FSMContext):
    """Отмена заказа клиентом"""
    try:
        # Получаем активный заказ клиента
        with Session() as session:
            order = session.query(Order).filter_by(
                client_id=callback.from_user.id
            ).filter(Order.status.in_(["pending", "accepted", "driver_arrived"])).order_by(
                Order.created_at.desc()).first()

            if not order:
                await callback.answer("❌ Активный заказ не найден")
                return

            order.status = "cancelled"
            order.cancellation_reason = "Cancelled by client"
            from datetime import datetime
            order.cancelled_at = datetime.now()
            session.commit()

            # Уведомляем водителя, если заказ был принят
            if order.driver_id:
                try:
                    await Bots.driver.send_message(
                        chat_id=order.driver_id,
                        text=f"❌ <b>Заказ #{order.id} отменен пассажиром</b>",
                        parse_mode="HTML"
                    )
                except:
                    pass

            await callback.message.edit_text(
                "❌ <b>Zamówienie anulowane</b>\n\n"
                "Twoje zamówienie zostało pomyślnie anulowane.",
                parse_mode="HTML"
            )
            await callback.answer("✅ Zamówienie anulowane")
            await state.clear()

    except Exception as e:
        logger.error(f"Error cancelling ride: {e}")
        await callback.answer("❌ Błąd podczas anulowania")


@taxi_router.callback_query(F.data == "show_driver_location")
async def show_driver_location(callback: CallbackQuery):
    """Показать местоположение водителя"""
    try:
        with Session() as session:
            order = session.query(Order).filter_by(
                client_id=callback.from_user.id
            ).filter(Order.status.in_(["accepted", "driver_arrived"])).order_by(Order.created_at.desc()).first()

            if not order or not order.driver_id:
                await callback.answer("❌ Водитель не найден")
                return

            # Отправляем примерное местоположение водителя
            # В реальной системе здесь должна быть актуальная геопозиция
            await callback.message.answer_location(
                latitude=order.pickup_lat + 0.001,  # Примерно рядом с точкой подачи
                longitude=order.pickup_lng + 0.001
            )
            await callback.answer("📍 Lokalizacja kierowcy")

    except Exception as e:
        logger.error(f"Error showing driver location: {e}")
        await callback.answer("❌ Błąd podczas pobierania lokalizacji")


@taxi_router.callback_query(F.data == "call_driver")
async def call_driver(callback: CallbackQuery):
    """Связаться с водителем"""
    await callback.answer(
        "📞 Funkcja dzwonienia zostanie wkrótce dodana",
        show_alert=True
    )


@taxi_router.callback_query(F.data == "call_support")
async def call_support(callback: CallbackQuery):
    """Связаться с поддержкой"""
    await callback.answer(
        "📞 Skontaktuj się z pomocą: @taxi_support_bot",
        show_alert=True
    )


# ===================================================================
# ОБРАБОТЧИКИ ВВОДА АДРЕСОВ ВРУЧНУЮ
# ===================================================================

@taxi_router.message(F.text.in_(["✍️ Wpisz adres ręcznie", "✍️ Ввести адрес вручную", "✍️ Enter Address Manually"]),
                     StateFilter(ClientStates.WAITING_PICKUP_LOCATION))
async def manual_pickup_address(message: Message, state: FSMContext):
    """Ручной ввод адреса подачи"""
    await message.answer(
        "📝 <b>Wpisz adres odbioru:</b>\n\n"
        "Przykład: ul. Wojska Polskiego 12, Szczecin",
        parse_mode="HTML"
    )
    await state.set_state(ClientStates.WAITING_PICKUP_LOCATION)


@taxi_router.message(F.text.in_(["✍️ Wpisz adres ręcznie", "✍️ Ввести адрес вручную", "✍️ Enter Address Manually"]),
                     StateFilter(ClientStates.WAITING_DESTINATION_LOCATION))
async def manual_destination_address(message: Message, state: FSMContext):
    """Ручной ввод адреса назначения"""
    await message.answer(
        "📝 <b>Wpisz adres docelowy:</b>\n\n"
        "Przykład: Galeria Kaskada, al. Niepodległości 36, Szczecin",
        parse_mode="HTML"
    )


@taxi_router.message(F.text, StateFilter(ClientStates.WAITING_PICKUP_LOCATION))
async def handle_pickup_address_text(message: Message, state: FSMContext):
    """Обработка текстового адреса подачи"""
    try:
        if message.text in ["❌ Anuluj", "❌ Отмена", "❌ Cancel"]:
            await state.clear()
            await message.answer("❌ Zamówienie anulowane")
            return

        # Геокодируем адрес
        pickup_location = await maps_service.geocode_address(message.text)

        # Сохраняем в состояние
        await state.update_data(pickup_location=pickup_location)

        language = await get_user_language(message.from_user.id)

        await message.answer(
            f"✅ <b>Miejsce odbioru:</b>\n{pickup_location.address}\n\n"
            f"📍 Teraz wyślij lokalizację docelową lub wpisz adres:",
            parse_mode="HTML",
            reply_markup=get_location_keyboard(language.value)
        )

        await state.set_state(ClientStates.WAITING_DESTINATION_LOCATION)

    except Exception as e:
        logger.error(f"Error handling pickup address text: {e}")
        await message.answer("❌ Nie można znaleźć tego adresu. Spróbuj ponownie.")


@taxi_router.message(F.text, StateFilter(ClientStates.WAITING_DESTINATION_LOCATION))
async def handle_destination_address_text(message: Message, state: FSMContext):
    """Обработка текстового адреса назначения"""
    try:
        if message.text in ["❌ Anuluj", "❌ Отмена", "❌ Cancel"]:
            await state.clear()
            await message.answer("❌ Zamówienie anulowane")
            return

        # Геокодируем адрес
        destination_location = await maps_service.geocode_address(message.text)

        # Сохраняем в состояние
        await state.update_data(destination_location=destination_location)

        language = await get_user_language(message.from_user.id)

        await message.answer(
            f"✅ <b>Miejsce docelowe:</b>\n{destination_location.address}\n\n"
            f"👥 Wybierz liczbę pasażerów:",
            parse_mode="HTML",
            reply_markup=get_passengers_keyboard(language.value)
        )

        await state.set_state(ClientStates.WAITING_PASSENGERS_COUNT)

    except Exception as e:
        logger.error(f"Error handling destination address text: {e}")
        await message.answer("❌ Nie można znaleźć tego adresu. Spróbuj ponownie.")


# ===================================================================
# ОБРАБОТЧИКИ ОТМЕНЫ
# ===================================================================

@taxi_router.message(F.text.in_(["❌ Anuluj", "❌ Отмена", "❌ Cancel"]))
async def cancel_order_process(message: Message, state: FSMContext):
    """Отмена процесса заказа"""
    await state.clear()

    language = await get_user_language(message.from_user.id)

    if language == Language.EN:
        text = "❌ Order cancelled. You can start over anytime."
    elif language == Language.RU:
        text = "❌ Заказ отменен. Вы можете начать заново в любое время."
    else:  # pl
        text = "❌ Zamówienie anulowane. Możesz zacząć od nowa w każdej chwili."

    await message.answer(
        text,
        reply_markup=get_main_menu_keyboard(language.value, UserRole.CLIENT)
    )


# ===================================================================
# ОБРАБОТЧИКИ УВЕДОМЛЕНИЙ О ИЗМЕНЕНИИ СТАТУСА (для интеграции)
# ===================================================================

@taxi_router.callback_query(F.data.startswith("ride_status_"))
async def handle_ride_status_update(callback: CallbackQuery):
    """Обработка обновлений статуса поездки"""
    try:
        status = callback.data.split("_")[2]

        with Session() as session:
            order = session.query(Order).filter_by(
                client_id=callback.from_user.id
            ).filter(Order.status.in_(["accepted", "driver_arrived", "in_progress"])).order_by(
                Order.created_at.desc()).first()

            if not order:
                await callback.answer("❌ Активный заказ не найден")
                return

            lang = await get_user_language_simple(callback.from_user.id)

            # Обновляем клавиатуру клиента в зависимости от статуса
            if status == "accepted":
                keyboard = get_client_ride_keyboard(lang, "accepted")
                status_text = "✅ Kierowca jedzie do Ciebie"
            elif status == "arrived":
                keyboard = get_client_ride_keyboard(lang, "arrived")
                status_text = "🚗 Kierowca przyjechał na miejsce"
            elif status == "in_progress":
                keyboard = get_client_ride_keyboard(lang, "in_progress")
                status_text = "🚦 Podróż rozpoczęta"
            else:
                keyboard = None
                status_text = "📱 Status zaktualizowany"

            if keyboard:
                await callback.message.edit_reply_markup(reply_markup=keyboard)

            await callback.answer(f"📱 {status_text}")

    except Exception as e:
        logger.error(f"Error handling ride status update: {e}")
        await callback.answer("❌ Błąd aktualizacji statusu")


# ===================================================================
# ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ОТЛАДКИ
# ===================================================================

@taxi_router.message(F.text.startswith("/client_status"))
async def check_client_status(message: Message):
    """Команда для проверки статуса клиента"""
    try:
        with Session() as session:
            # Найти активный заказ клиента
            active_order = session.query(Order).filter_by(
                client_id=message.from_user.id
            ).filter(Order.status.not_in(["completed", "cancelled"])).order_by(Order.created_at.desc()).first()

            if not active_order:
                await message.answer("📊 <b>СТАТУС КЛИЕНТА</b>\n\n❌ Нет активных заказов", parse_mode="HTML")
                return

            result_text = (
                f"📊 <b>СТАТУС КЛИЕНТА</b>\n\n"
                f"🆔 <b>Заказ:</b> #{active_order.id}\n"
                f"📋 <b>Статус:</b> {active_order.status}\n"
                f"📍 <b>Откуда:</b> {active_order.pickup_address}\n"
                f"📍 <b>Куда:</b> {active_order.destination_address}\n"
                f"👥 <b>Пассажиров:</b> {getattr(active_order, 'passengers_count', 1)}\n"
                f"💵 <b>Стоимость:</b> {getattr(active_order, 'estimated_price', getattr(active_order, 'price', 0))} zł\n"
                f"🕒 <b>Создан:</b> {active_order.created_at.strftime('%H:%M:%S')}"
            )

            if active_order.driver_id:
                result_text += f"\n👤 <b>Водитель:</b> {active_order.driver_name or active_order.driver_id}"

            if active_order.started_at:
                result_text += f"\n🚦 <b>Начат:</b> {active_order.started_at.strftime('%H:%M:%S')}"

            # Добавляем соответствующие кнопки
            lang = await get_user_language_simple(message.from_user.id)
            keyboard = None

            if active_order.status == "pending":
                keyboard = get_client_ride_keyboard(lang, "pending")
            elif active_order.status == "accepted":
                keyboard = get_client_ride_keyboard(lang, "accepted")
            elif active_order.status == "in_progress":
                keyboard = get_client_ride_keyboard(lang, "in_progress")

            await message.answer(result_text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Ошибка проверки статуса: {e}")


# ===================================================================
# УНИВЕРСАЛЬНЫЙ ПЕРЕХВАТЧИК CALLBACK ДЛЯ ОТЛАДКИ
# ===================================================================

@taxi_router.callback_query()
async def catch_unhandled_taxi_callbacks(callback: CallbackQuery):
    """Перехватывает все необработанные callback в taxi_ride"""
    print(f"🔧 [TAXI DEBUG] Unhandled callback: {callback.data}")
    await callback.answer(f"🔧 TAXI DEBUG: Callback '{callback.data}' получен но не обработан")
    logger.warning(f"Unhandled taxi callback: {callback.data} from user {callback.from_user.id}")


# ===================================================================
# МЕНЕДЖЕР СТАТУСОВ
# ===================================================================

class RideStatusManager:
    """Менеджер статусов поездок для клиента"""

    @staticmethod
    def get_status_text(status: str, language: str = "pl") -> str:
        """Получить текст статуса на нужном языке"""
        status_texts = {
            "pending": {
                "pl": "⏳ Szukamy kierowcy",
                "en": "⏳ Looking for driver",
                "ru": "⏳ Ищем водителя"
            },
            "accepted": {
                "pl": "✅ Kierowca jedzie do Ciebie",
                "en": "✅ Driver is coming to you",
                "ru": "✅ Водитель едет к вам"
            },
            "driver_arrived": {
                "pl": "🚗 Kierowca przyjechał",
                "en": "🚗 Driver has arrived",
                "ru": "🚗 Водитель прибыл"
            },
            "in_progress": {
                "pl": "🚦 Podróż w toku",
                "en": "🚦 Trip in progress",
                "ru": "🚦 Поездка началась"
            },
            "completed": {
                "pl": "🏁 Podróż zakończona",
                "en": "🏁 Trip completed",
                "ru": "🏁 Поездка завершена"
            },
            "cancelled": {
                "pl": "❌ Anulowane",
                "en": "❌ Cancelled",
                "ru": "❌ Отменено"
            }
        }

        return status_texts.get(status, {}).get(language, status)


# ===================================================================
# ЭКСПОРТ ФУНКЦИЙ
# ===================================================================

__all__ = [
    'taxi_router',
    'RideStatusManager'
]