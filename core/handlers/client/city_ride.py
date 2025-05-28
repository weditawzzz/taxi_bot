"""
Хэндлеры для заказа такси по городу
"""
import logging
from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove

from core.services import UserService, MapsService, PriceCalculatorService, Location
from core.models import UserRole
from core.exceptions import NotFoundError
from core.utils.localization import get_text, Language
from core.keyboards import (
    get_main_menu_keyboard, get_location_keyboard,
    get_passengers_keyboard, get_ride_confirmation_keyboard
)
from core.states import ClientStates

logger = logging.getLogger(__name__)

# Роутер для заказа поездок
city_ride_router = Router()

# Создаем сервисы
user_service = UserService()
maps_service = MapsService()
price_calculator = PriceCalculatorService()


async def get_user_language(telegram_id: int) -> Language:
    """Получить язык пользователя"""
    try:
        user = await user_service.get_user_by_telegram_id(telegram_id)
        if user and user.language in ['en', 'pl', 'ru']:
            return Language(user.language)
        return Language.PL
    except Exception:
        return Language.PL


@city_ride_router.message(StateFilter(ClientStates.WAITING_PICKUP_LOCATION))
async def handle_pickup_location(message: Message, state: FSMContext) -> None:
    """Обработка локации подачи"""
    try:
        language = await get_user_language(message.from_user.id)

        # Проверяем отмену
        if message.text and message.text in ["❌ Anuluj", "❌ Отмена", "❌ Cancel"]:
            await cancel_order(message, state, language)
            return

        pickup_location = None

        if message.location:
            # Получена геолокация
            address = await maps_service.reverse_geocode(
                message.location.latitude,
                message.location.longitude
            )
            pickup_location = Location(
                latitude=message.location.latitude,
                longitude=message.location.longitude,
                address=address
            )

        elif message.text and message.text not in ["✍️ Wpisz adres ręcznie", "✍️ Ввести адрес вручную", "✍️ Enter Address Manually"]:
            # Получен текстовый адрес
            try:
                pickup_location = await maps_service.geocode_address(message.text)
            except NotFoundError:
                error_text = get_text("address_not_found", language)
                await message.answer(error_text)
                return
            except Exception as e:
                logger.error(f"Geocoding error: {e}")
                # Создаем простую локацию для Щецина
                pickup_location = Location(
                    latitude=53.4285,
                    longitude=14.5528,
                    address=f"Szczecin, {message.text}"
                )

        elif message.text in ["✍️ Wpisz adres ręcznie", "✍️ Ввести адрес вручную", "✍️ Enter Address Manually"]:
            text = get_text("enter_pickup_address", language)
            await message.answer(text, reply_markup=ReplyKeyboardRemove())
            return

        if not pickup_location:
            error_text = get_text("invalid_location", language)
            await message.answer(error_text)
            return

        # Сохраняем локацию подачи
        await state.update_data(pickup_location=pickup_location)

        # Запрашиваем место назначения
        text = get_text("send_destination_location", language)
        keyboard = get_location_keyboard(language.value)

        await message.answer(text, reply_markup=keyboard)
        await state.set_state(ClientStates.WAITING_DESTINATION_LOCATION)

    except Exception as e:
        logger.error(f"Error handling pickup location: {e}")
        await message.answer("❌ Wystąpił błąd. Spróbuj ponownie.")


@city_ride_router.message(StateFilter(ClientStates.WAITING_DESTINATION_LOCATION))
async def handle_destination_location(message: Message, state: FSMContext) -> None:
    """Обработка места назначения"""
    try:
        language = await get_user_language(message.from_user.id)

        # Проверяем отмену
        if message.text and message.text in ["❌ Anuluj", "❌ Отмена", "❌ Cancel"]:
            await cancel_order(message, state, language)
            return

        destination_location = None

        if message.location:
            address = await maps_service.reverse_geocode(
                message.location.latitude,
                message.location.longitude
            )
            destination_location = Location(
                latitude=message.location.latitude,
                longitude=message.location.longitude,
                address=address
            )

        elif message.text and message.text not in ["✍️ Wpisz adres", "✍️ Ввести адрес", "✍️ Enter Address"]:
            try:
                destination_location = await maps_service.geocode_address(message.text)
            except NotFoundError:
                error_text = get_text("address_not_found", language)
                await message.answer(error_text)
                return
            except Exception as e:
                logger.error(f"Geocoding error: {e}")
                # Создаем простую локацию для Щецина
                destination_location = Location(
                    latitude=53.4470,
                    longitude=14.5524,
                    address=f"Szczecin, {message.text}"
                )

        elif message.text in ["✍️ Wpisz adres", "✍️ Ввести адрес", "✍️ Enter Address"]:
            text = get_text("enter_destination_address", language)
            await message.answer(text, reply_markup=ReplyKeyboardRemove())
            return

        if not destination_location:
            error_text = get_text("invalid_location", language)
            await message.answer(error_text)
            return

        # Сохраняем место назначения
        await state.update_data(destination_location=destination_location)

        # Запрашиваем количество пассажиров
        text = get_text("enter_passengers_count", language)
        keyboard = get_passengers_keyboard(language.value)

        await message.answer(text, reply_markup=keyboard)
        await state.set_state(ClientStates.WAITING_PASSENGERS_COUNT)

    except Exception as e:
        logger.error(f"Error handling destination location: {e}")
        await message.answer("❌ Wystąpił błąd. Spróbuj ponownie.")


@city_ride_router.message(StateFilter(ClientStates.WAITING_PASSENGERS_COUNT))
async def handle_passengers_count(message: Message, state: FSMContext) -> None:
    """Обработка количества пассажиров"""
    try:
        language = await get_user_language(message.from_user.id)

        # Проверяем отмену
        if message.text and message.text in ["❌ Anuluj", "❌ Отмена", "❌ Cancel"]:
            await cancel_order(message, state, language)
            return

        try:
            passengers_count = int(message.text)
            if passengers_count < 1 or passengers_count > 4:
                raise ValueError()
        except ValueError:
            error_text = get_text("invalid_passengers_count", language)
            await message.answer(error_text)
            return

        # Получаем данные заказа
        data = await state.get_data()
        pickup_location = data.get('pickup_location')
        destination_location = data.get('destination_location')

        if not pickup_location or not destination_location:
            await message.answer("❌ Dane lokalizacji utracone. Rozpocznij ponownie.")
            await state.clear()
            return

        try:
            # Рассчитываем маршрут и стоимость
            route_info = await maps_service.get_route(pickup_location, destination_location)
            estimated_price = price_calculator.calculate_price(
                route_info.distance_km,
                route_info.duration_minutes
            )

            logger.info(f"Route calculated: {route_info.distance_km}km, {route_info.duration_minutes}min, {estimated_price}PLN")

        except Exception as e:
            logger.error(f"Error calculating route/price: {e}")
            # Fallback расчет
            distance = pickup_location.distance_to(destination_location)
            estimated_price = price_calculator.calculate_price(distance, int(distance * 2))

            # Создаем простой route_info
            class SimpleRoute:
                def __init__(self):
                    self.distance_km = distance
                    self.duration_minutes = int(distance * 2)

            route_info = SimpleRoute()

        # Сохраняем все данные
        await state.update_data(
            passengers_count=passengers_count,
            route_info=route_info,
            estimated_price=estimated_price
        )

        # Показываем сводку заказа
        summary_text = get_text(
            "ride_summary",
            language,
            pickup=pickup_location.address,
            destination=destination_location.address,
            distance=f"{route_info.distance_km:.1f}",
            duration=route_info.duration_minutes,
            price=str(estimated_price),
            passengers=passengers_count
        )

        keyboard = get_ride_confirmation_keyboard(language.value)

        await message.answer(
            summary_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(ClientStates.WAITING_RIDE_CONFIRMATION)

    except Exception as e:
        logger.error(f"Error handling passengers count: {e}")
        await message.answer("❌ Wystąpił błąd. Spróbuj ponownie.")


@city_ride_router.callback_query(F.data == "confirm_ride", StateFilter(ClientStates.WAITING_RIDE_CONFIRMATION))
async def confirm_ride(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение заказа"""
    try:
        language = await get_user_language(callback.from_user.id)

        # Получаем данные заказа
        data = await state.get_data()
        pickup_location = data.get('pickup_location')
        destination_location = data.get('destination_location')
        passengers_count = data.get('passengers_count')
        route_info = data.get('route_info')
        estimated_price = data.get('estimated_price')

        # Генерируем ID заказа
        import random
        ride_id = f"TX{random.randint(1000, 9999)}"

        # Сохраняем заказ в базу данных
        try:
            from core.models import Ride, RideStatus
            from core.database import get_session

            async with get_session() as session:
                ride = Ride(
                    client_id=callback.from_user.id,
                    user_id=callback.from_user.id,  # Для совместимости
                    pickup_address=pickup_location.address,
                    pickup_lat=pickup_location.latitude,
                    pickup_lng=pickup_location.longitude,
                    destination_address=destination_location.address,
                    destination_lat=destination_location.latitude,
                    destination_lng=destination_location.longitude,
                    distance_km=route_info.distance_km,
                    duration_minutes=route_info.duration_minutes,
                    estimated_price=estimated_price,
                    price=estimated_price,  # Для совместимости
                    status=RideStatus.PENDING,
                    passengers_count=passengers_count,
                    order_type="city_ride",
                    payment_method="cash"
                )

                session.add(ride)
                await session.commit()
                await session.refresh(ride)

                logger.info(f"Ride saved to database: {ride.id}")

                # Отправляем уведомление водителям через новый сервис
                from core.services.driver_notification import driver_notification_service

                await driver_notification_service.notify_all_drivers(ride.id, {
                    'pickup_address': pickup_location.address,
                    'destination_address': destination_location.address,
                    'distance_km': route_info.distance_km,
                    'estimated_price': estimated_price,
                    'passengers_count': passengers_count,
                    'order_type': 'city_ride'
                })

        except Exception as e:
            logger.error(f"Error saving ride: {e}")
            await callback.answer("❌ Błąd zapisywania zamówienia")
            return

        success_text = get_text(
            "ride_created",
            language,
            ride_id=ride_id
        )

        await callback.message.edit_text(success_text, parse_mode="HTML")
        await callback.answer()
        await state.clear()

        # Возвращаем главное меню
        main_keyboard = get_main_menu_keyboard(language.value, UserRole.CLIENT)
        await callback.message.answer(
            get_text("main_menu", language),
            reply_markup=main_keyboard
        )

        logger.info(f"Ride created successfully: {ride_id}")

    except Exception as e:
        logger.error(f"Error confirming ride: {e}")
        await callback.answer("❌ Wystąpił błąd. Spróbuj ponownie.")


async def notify_driver_about_ride(ride_id: int, ride_data: dict):
    """Уведомление водителя о новом заказе такси"""
    try:
        from core.bot_instance import Bots
        from core.config import Config
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Przyjmij", callback_data=f"accept_{ride_id}")
        builder.button(text="❌ Odrzuć", callback_data=f"reject_{ride_id}")

        text = (
            "🚖 <b>NOWE ZAMÓWIENIE TAXI</b>\n\n"
            f"📍 <b>Z:</b> {ride_data['pickup_address']}\n"
            f"📍 <b>Do:</b> {ride_data['destination_address']}\n\n"
            f"📏 <b>Odległość:</b> {ride_data['distance_km']:.1f} km\n"
            f"👥 <b>Pasażerów:</b> {ride_data['passengers_count']}\n"
            f"💵 <b>Cena:</b> {ride_data['estimated_price']} zł\n\n"
            f"⏰ <b>Czas na odpowiedź:</b> 60 sekund"
        )

        await Bots.driver.send_message(
            chat_id=Config.DRIVER_CHAT_ID,
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )

        logger.info(f"Driver notified about ride {ride_id}")

    except Exception as e:
        logger.error(f"Error notifying driver about ride {ride_id}: {e}")


async def notify_driver_about_ride(ride_id: int, ride_data: dict):
    """Уведомление водителя о новом заказе такси"""
    try:
        from core.bot_instance import Bots
        from core.config import Config
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Przyjmij", callback_data=f"accept_{ride_id}")
        builder.button(text="❌ Odrzuć", callback_data=f"reject_{ride_id}")

        text = (
            "🚖 <b>NOWE ZAMÓWIENIE TAXI</b>\n\n"
            f"📍 <b>Z:</b> {ride_data['pickup_address']}\n"
            f"📍 <b>Do:</b> {ride_data['destination_address']}\n\n"
            f"📏 <b>Odległość:</b> {ride_data['distance_km']:.1f} km\n"
            f"👥 <b>Pasażerów:</b> {ride_data['passengers_count']}\n"
            f"💵 <b>Cena:</b> {ride_data['estimated_price']} zł\n\n"
            f"⏰ <b>Czas na odpowiedź:</b> 60 sekund"
        )

        await Bots.driver.send_message(
            chat_id=Config.DRIVER_CHAT_ID,
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )

        logger.info(f"Driver notified about ride {ride_id}")

    except Exception as e:
        logger.error(f"Error notifying driver about ride {ride_id}: {e}")


@city_ride_router.callback_query(F.data == "cancel_ride")
async def cancel_ride_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена заказа через callback"""
    try:
        language = await get_user_language(callback.from_user.id)
        await cancel_order(callback.message, state, language)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error cancelling ride: {e}")
        await callback.answer("❌ Wystąpił błąd.")


async def cancel_order(message: Message, state: FSMContext, language: Language) -> None:
    """Отмена заказа"""
    try:
        cancel_text = get_text("order_cancelled", language)
        main_keyboard = get_main_menu_keyboard(language.value, UserRole.CLIENT)

        await message.answer(
            cancel_text,
            reply_markup=main_keyboard
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Error cancelling order: {e}")