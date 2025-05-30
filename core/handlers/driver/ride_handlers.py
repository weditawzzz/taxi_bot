"""
Обработчики для управления поездкой водителем с системой счетчика ожидания
"""
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict
from urllib.parse import quote

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.models import Session, Ride as Order
from core.bot_instance import Bots
from core.keyboards import get_driver_ride_keyboard, get_location_sharing_keyboard

logger = logging.getLogger(__name__)
driver_ride_router = Router()

# ===================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ СИСТЕМЫ ОЖИДАНИЯ
# ===================================================================

# Словарь для хранения активных счетчиков ожидания
# {ride_id: {'start_time': datetime, 'driver_id': int}}
waiting_timers: Dict[int, Dict] = {}

# ===================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ===================================================================

async def get_user_language_simple(user_id: int) -> str:
    """Простая функция получения языка пользователя"""
    try:
        from core.services.user_service import UserService
        user_service = UserService()
        user = await user_service.get_user_by_telegram_id(user_id)
        return user.language if user and user.language else "pl"
    except Exception:
        return "pl"


async def get_current_ride_id(user_id: int) -> Optional[int]:
    """Получение ID текущей активной поездки пользователя"""
    try:
        with Session() as session:
            order = session.query(Order).filter(
                Order.driver_id == user_id,
                Order.status.in_(["accepted", "driver_arrived", "in_progress"])
            ).order_by(Order.created_at.desc()).first()

            return order.id if order else None

    except Exception as e:
        logger.error(f"Error getting current ride ID: {e}")
        return None


def get_waiting_management_keyboard(language: str = "pl"):
    """Клавиатура управления ожиданием для водителя"""
    builder = InlineKeyboardBuilder()

    if language == "en":
        builder.button(text="📊 Check Time", callback_data="check_waiting_time")
        builder.button(text="▶️ Continue Trip", callback_data="end_waiting")
        builder.button(text="🏁 Complete Trip", callback_data="complete_trip")
    elif language == "ru":
        builder.button(text="📊 Проверить время", callback_data="check_waiting_time")
        builder.button(text="▶️ Продолжить поездку", callback_data="end_waiting")
        builder.button(text="🏁 Завершить поездку", callback_data="complete_trip")
    else:  # Polish
        builder.button(text="📊 Sprawdź czas", callback_data="check_waiting_time")
        builder.button(text="▶️ Kontynuuj podróż", callback_data="end_waiting")
        builder.button(text="🏁 Zakończ podróż", callback_data="complete_trip")

    builder.adjust(2, 1)
    return builder.as_markup()


def get_driver_waiting_response_keyboard(language: str = "pl"):
    """Клавиатура для ответа водителя на запрос остановки"""
    builder = InlineKeyboardBuilder()

    if language == "en":
        builder.button(text="⏸️ Stop & Start Timer", callback_data="accept_waiting")
        builder.button(text="❌ Cannot Stop", callback_data="decline_waiting")
    elif language == "ru":
        builder.button(text="⏸️ Остановиться и запустить таймер", callback_data="accept_waiting")
        builder.button(text="❌ Не могу остановиться", callback_data="decline_waiting")
    else:  # Polish
        builder.button(text="⏸️ Zatrzymaj i uruchom licznik", callback_data="accept_waiting")
        builder.button(text="❌ Nie mogę się zatrzymać", callback_data="decline_waiting")

    builder.adjust(1)
    return builder.as_markup()


def get_passenger_waiting_keyboard(language: str = "pl"):
    """Клавиатура для пассажира во время ожидания"""
    builder = InlineKeyboardBuilder()

    if language == "en":
        builder.button(text="✅ Ready to Continue", callback_data="ready_to_continue")
        builder.button(text="📊 Check Cost", callback_data="check_waiting_cost")
    elif language == "ru":
        builder.button(text="✅ Готов продолжить", callback_data="ready_to_continue")
        builder.button(text="📊 Проверить стоимость", callback_data="check_waiting_cost")
    else:  # Polish
        builder.button(text="✅ Gotowy do kontynuacji", callback_data="ready_to_continue")
        builder.button(text="📊 Sprawdź koszt", callback_data="check_waiting_cost")

    builder.adjust(1)
    return builder.as_markup()


# ===================================================================
# ФУНКЦИИ УПРАВЛЕНИЯ СЧЕТЧИКОМ ОЖИДАНИЯ
# ===================================================================

async def start_waiting_counter(ride_id: int, driver_id: int):
    """Запуск счетчика ожидания"""
    try:
        current_time = datetime.now()

        # Сохраняем в глобальный словарь
        waiting_timers[ride_id] = {
            'start_time': current_time,
            'driver_id': driver_id
        }

        # Обновляем базу данных
        with Session() as session:
            order = session.query(Order).get(ride_id)
            if order:
                # Добавляем поля ожидания если их нет
                if not hasattr(order, 'waiting_started_at'):
                    # Для обратной совместимости - используем notes поле
                    waiting_info = {
                        'waiting_started_at': current_time.isoformat(),
                        'waiting_status': 'active'
                    }
                    if hasattr(order, 'notes') and order.notes:
                        try:
                            existing_notes = json.loads(order.notes)
                            existing_notes.update(waiting_info)
                            order.notes = json.dumps(existing_notes)
                        except:
                            order.notes = json.dumps(waiting_info)
                    else:
                        order.notes = json.dumps(waiting_info)
                else:
                    order.waiting_started_at = current_time

                session.commit()

        logger.info(f"Waiting counter started for ride {ride_id}")

    except Exception as e:
        logger.error(f"Error starting waiting counter: {e}")


async def stop_waiting_counter(ride_id: int) -> Optional[dict]:
    """Остановка счетчика ожидания"""
    try:
        if ride_id not in waiting_timers:
            return None

        # Получаем информацию о времени
        start_time = waiting_timers[ride_id]['start_time']
        end_time = datetime.now()
        elapsed = end_time - start_time
        minutes = max(1, int(elapsed.total_seconds() / 60))  # Минимум 1 минута
        cost = Decimal(str(minutes))

        # Обновляем базу данных
        with Session() as session:
            order = session.query(Order).get(ride_id)
            if order:
                # Обновляем существующую стоимость
                base_price = getattr(order, 'estimated_price', getattr(order, 'price', Decimal('0')))
                if isinstance(base_price, (int, float)):
                    base_price = Decimal(str(base_price))

                total_price = base_price + cost

                # Сохраняем информацию о ожидании в notes
                waiting_log = {
                    'waiting_started_at': start_time.isoformat(),
                    'waiting_ended_at': end_time.isoformat(),
                    'waiting_minutes': minutes,
                    'waiting_cost': float(cost),
                    'waiting_status': 'completed'
                }

                if hasattr(order, 'notes') and order.notes:
                    try:
                        existing_notes = json.loads(order.notes)
                        if isinstance(existing_notes, dict):
                            existing_notes.update(waiting_log)
                        else:
                            existing_notes = waiting_log
                        order.notes = json.dumps(existing_notes)
                    except:
                        order.notes = json.dumps(waiting_log)
                else:
                    order.notes = json.dumps(waiting_log)

                # Обновляем цену
                if hasattr(order, 'final_price'):
                    order.final_price = total_price
                else:
                    # Для обратной совместимости используем existing field
                    if hasattr(order, 'estimated_price'):
                        order.estimated_price = total_price
                    elif hasattr(order, 'price'):
                        order.price = total_price

                session.commit()

        # Удаляем из активных таймеров
        del waiting_timers[ride_id]

        logger.info(f"Waiting counter stopped for ride {ride_id}: {minutes} min, {cost} zł")

        return {
            'minutes': minutes,
            'cost': cost,
            'start_time': start_time,
            'end_time': end_time
        }

    except Exception as e:
        logger.error(f"Error stopping waiting counter: {e}")
        return None


async def notify_passenger_waiting_started(ride_id: int):
    """Уведомление пассажира о начале ожидания"""
    try:
        with Session() as session:
            order = session.query(Order).get(ride_id)
            if not order:
                return

            client_id = getattr(order, 'client_id', getattr(order, 'user_id', None))
            if not client_id:
                return

            text = (
                "⏸️ <b>OCZEKIWANIE ROZPOCZĘTE</b>\n\n"
                "⏰ <b>Taryfa:</b> 1 zł/minuta\n"
                "🕐 <b>Czas rozpoczęcia:</b> " + datetime.now().strftime("%H:%M:%S") + "\n\n"
                "Gdy będziesz gotowy do kontynuacji podróży, naciśnij przycisk poniżej:"
            )

            keyboard = get_passenger_waiting_keyboard("pl")

            await Bots.client.send_message(
                chat_id=client_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )

    except Exception as e:
        logger.error(f"Error notifying passenger about waiting start: {e}")


async def notify_passenger_waiting_declined(ride_id: int):
    """Уведомление пассажира об отклонении запроса остановки"""
    try:
        with Session() as session:
            order = session.query(Order).get(ride_id)
            if not order:
                return

            client_id = getattr(order, 'client_id', getattr(order, 'user_id', None))
            if not client_id:
                return

            text = (
                "❌ <b>Prośba o zatrzymanie odrzucona</b>\n\n"
                "Kierowca nie może się zatrzymać w tym momencie.\n"
                "Podróż kontynuowana w normalnym trybie."
            )

            await Bots.client.send_message(
                chat_id=client_id,
                text=text,
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error notifying passenger about waiting decline: {e}")


async def notify_passenger_waiting_ended(ride_id: int, waiting_info: dict):
    """Уведомление пассажира о завершении ожидания"""
    try:
        with Session() as session:
            order = session.query(Order).get(ride_id)
            if not order:
                return

            client_id = getattr(order, 'client_id', getattr(order, 'user_id', None))
            if not client_id:
                return

            text = (
                f"▶️ <b>OCZEKIWANIE ZAKOŃCZONE</b>\n\n"
                f"⏱️ <b>Czas oczekiwania:</b> {waiting_info['minutes']} min\n"
                f"💰 <b>Koszt oczekiwania:</b> {waiting_info['cost']} zł\n\n"
                f"Podróż jest kontynuowana..."
            )

            await Bots.client.send_message(
                chat_id=client_id,
                text=text,
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error notifying passenger about waiting end: {e}")


# ===================================================================
# ОБРАБОТЧИКИ СИСТЕМЫ ОЖИДАНИЯ
# ===================================================================

@driver_ride_router.callback_query(F.data == "accept_waiting")
async def accept_waiting(callback: CallbackQuery, state: FSMContext):
    """Водитель принимает запрос остановки и запускает счетчик"""
    try:
        ride_id = await get_current_ride_id(callback.from_user.id)

        if not ride_id:
            await callback.answer("❌ Активная поездка не найдена")
            return

        # Запускаем счетчик ожидания
        await start_waiting_counter(ride_id, callback.from_user.id)

        # Уведомляем водителя
        text = (
            "⏸️ <b>LICZNIK OCZEKIWANIA URUCHOMIONY</b>\n\n"
            "⏰ <b>Taryfa:</b> 1 zł/minuta\n"
            "🕐 <b>Czas rozpoczęcia:</b> " + datetime.now().strftime("%H:%M:%S") + "\n\n"
            "Zarządzanie oczekiwaniem:"
        )

        keyboard = get_waiting_management_keyboard("pl")

        await callback.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        # Уведомляем пассажира
        await notify_passenger_waiting_started(ride_id)

        await callback.answer("✅ Licznik oczekiwania uruchomiony")

    except Exception as e:
        logger.error(f"Error accepting waiting: {e}")
        await callback.answer("❌ Błąd podczas uruchamiania licznika")


@driver_ride_router.callback_query(F.data == "decline_waiting")
async def decline_waiting(callback: CallbackQuery):
    """Водитель отклоняет запрос остановки"""
    try:
        ride_id = await get_current_ride_id(callback.from_user.id)

        if not ride_id:
            await callback.answer("❌ Активная поездка не найдена")
            return

        # Уведомляем пассажира об отклонении
        await notify_passenger_waiting_declined(ride_id)

        # Обновляем сообщение водителя
        text = "❌ <b>Prośba o zatrzymanie odrzucona</b>\n\nPodróż kontynuowana w normalnym trybie."

        # Возвращаем обычную клавиатуру управления поездкой
        lang = await get_user_language_simple(callback.from_user.id)
        keyboard = get_driver_ride_keyboard(lang, "in_progress")

        await callback.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        await callback.answer("❌ Prośba o zatrzymanie odrzucona")

    except Exception as e:
        logger.error(f"Error declining waiting: {e}")
        await callback.answer("❌ Błąd podczas odrzucania prośby")


@driver_ride_router.callback_query(F.data == "check_waiting_time")
async def check_waiting_time(callback: CallbackQuery):
    """Проверка текущего времени ожидания"""
    try:
        ride_id = await get_current_ride_id(callback.from_user.id)

        if not ride_id or ride_id not in waiting_timers:
            await callback.answer("❌ Licznik oczekiwania nie jest aktywny")
            return

        # Вычисляем текущее время ожидания
        start_time = waiting_timers[ride_id]['start_time']
        current_time = datetime.now()
        elapsed = current_time - start_time
        minutes = int(elapsed.total_seconds() / 60)
        cost = Decimal(str(max(1, minutes)))  # Минимум 1 минута

        text = (
            f"📊 <b>AKTUALNY CZAS OCZEKIWANIA</b>\n\n"
            f"⏰ <b>Czas rozpoczęcia:</b> {start_time.strftime('%H:%M:%S')}\n"
            f"⏱️ <b>Upłynęło czasu:</b> {minutes} min\n"
            f"💰 <b>Aktualny koszt:</b> {cost} zł\n\n"
            f"<i>Taryfa: 1 zł/minuta</i>"
        )

        await callback.answer(text, show_alert=True)

    except Exception as e:
        logger.error(f"Error checking waiting time: {e}")
        await callback.answer("❌ Błąd podczas sprawdzania czasu")


@driver_ride_router.callback_query(F.data == "end_waiting")
async def end_waiting(callback: CallbackQuery):
    """Завершение ожидания и продолжение поездки"""
    try:
        ride_id = await get_current_ride_id(callback.from_user.id)

        if not ride_id:
            await callback.answer("❌ Активная поездка не найдена")
            return

        # Останавливаем счетчик ожидания
        waiting_info = await stop_waiting_counter(ride_id)

        if not waiting_info:
            await callback.answer("❌ Licznik oczekiwania nie był aktywny")
            return

        # Уведомляем водителя о завершении ожидания
        text = (
            f"▶️ <b>OCZEKIWANIE ZAKOŃCZONE</b>\n\n"
            f"⏱️ <b>Czas oczekiwania:</b> {waiting_info['minutes']} min\n"
            f"💰 <b>Koszt oczekiwania:</b> {waiting_info['cost']} zł\n\n"
            f"Podróż jest kontynuowana..."
        )

        # Возвращаем обычные кнопки управления поездкой
        lang = await get_user_language_simple(callback.from_user.id)
        keyboard = get_driver_ride_keyboard(lang, "in_progress")

        await callback.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        # Уведомляем пассажира
        await notify_passenger_waiting_ended(ride_id, waiting_info)

        await callback.answer("✅ Oczekiwanie zakończone, podróż kontynuowana")

    except Exception as e:
        logger.error(f"Error ending waiting: {e}")
        await callback.answer("❌ Błąd podczas kończenia oczekiwania")


@driver_ride_router.callback_query(F.data == "ready_to_continue")
async def passenger_ready_to_continue(callback: CallbackQuery):
    """Пассажир готов продолжить поездку"""
    try:
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

    except Exception as e:
        logger.error(f"Error notifying driver passenger ready: {e}")
        await callback.answer("❌ Błąd podczas powiadamiania kierowcy")


@driver_ride_router.callback_query(F.data == "check_waiting_cost")
async def check_waiting_cost_passenger(callback: CallbackQuery):
    """Пассажир проверяет стоимость ожидания"""
    try:
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

            await callback.answer(text, show_alert=True)

    except Exception as e:
        logger.error(f"Error checking waiting cost for passenger: {e}")
        await callback.answer("❌ Błąd podczas sprawdzania kosztu")


# ===================================================================
# ОБРАБОТЧИКИ УПРАВЛЕНИЯ СТАТУСОМ ПОЕЗДКИ (ОБНОВЛЕННЫЕ)
# ===================================================================

@driver_ride_router.callback_query(F.data == "driver_arrived")
async def driver_arrived(callback: CallbackQuery, state: FSMContext):
    """Водитель прибыл к пассажиру"""
    try:
        with Session() as session:
            order = session.query(Order).filter_by(
                driver_id=callback.from_user.id,
                status="accepted"
            ).order_by(Order.created_at.desc()).first()

            if not order:
                await callback.answer("❌ Активный заказ не найден")
                return

            # Обновляем статус
            order.status = "driver_arrived"
            order.accepted_at = datetime.now()
            session.commit()

            # Уведомляем пассажира
            client_id = getattr(order, 'client_id', getattr(order, 'user_id', None))
            if client_id:
                from core.keyboards import get_client_ride_keyboard
                lang = await get_user_language_simple(client_id)

                await Bots.client.send_message(
                    chat_id=client_id,
                    text=(
                        "✅ <b>Kierowca przyjechał!</b>\n\n"
                        "🚗 Twój kierowca już na miejscu i czeka na Ciebie.\n"
                        "Sprawdź numer rejestracyjny i wsiadaj do samochodu."
                    ),
                    reply_markup=get_client_ride_keyboard(lang, "arrived"),
                    parse_mode="HTML"
                )

            # Обновляем клавиатуру водителя
            lang = await get_user_language_simple(callback.from_user.id)

            await callback.message.edit_text(
                f"✅ <b>PRZYJECHAŁEŚ DO PASAŻERA</b>\n\n"
                f"📍 Adres: {order.pickup_address}\n"
                f"👥 Pasażerów: {getattr(order, 'passengers_count', 1)}\n\n"
                f"🎯 Czekaj na pasażera i naciśnij 'Rozpocznij podróż' gdy wsiądzie do samochodu.",
                reply_markup=get_driver_ride_keyboard(lang, "arrived"),
                parse_mode="HTML"
            )
            await callback.answer("✅ Status zaktualizowany - przyjechałeś")

    except Exception as e:
        logger.error(f"Error updating driver arrival: {e}")
        await callback.answer("❌ Błąd podczas aktualizacji statusu")


@driver_ride_router.callback_query(F.data == "start_trip")
async def start_trip(callback: CallbackQuery, state: FSMContext):
    """Начать поездку"""
    try:
        with Session() as session:
            order = session.query(Order).filter_by(
                driver_id=callback.from_user.id,
                status="driver_arrived"
            ).order_by(Order.created_at.desc()).first()

            if not order:
                await callback.answer("❌ Заказ не найден или статус неверный")
                return

            # Обновляем статус
            order.status = "in_progress"
            order.started_at = datetime.now()
            session.commit()

            # Уведомляем пассажира с кнопкой запроса остановки
            client_id = getattr(order, 'client_id', getattr(order, 'user_id', None))
            if client_id:
                # Создаем клавиатуру с кнопкой запроса остановки
                passenger_keyboard = InlineKeyboardBuilder()
                passenger_keyboard.button(text="🛑 Poproś o zatrzymanie", callback_data="request_stop")
                passenger_keyboard.button(text="📍 Obecna lokalizacja", callback_data="current_location")
                passenger_keyboard.adjust(1)

                await Bots.client.send_message(
                    chat_id=client_id,
                    text=(
                        "🚦 <b>Podróż rozpoczęta!</b>\n\n"
                        f"📍 Cel: {order.destination_address}\n"
                        f"💵 Koszt: {getattr(order, 'estimated_price', getattr(order, 'price', 0))} zł\n\n"
                        "Życzymy miłej podróży!\n\n"
                        "ℹ️ <b>Dodatkowe opcje:</b>\n"
                        "• Możesz poprosić o zatrzymanie (1 zł/minuta)\n"
                        "• Sprawdzić bieżącą lokalizację"
                    ),
                    reply_markup=passenger_keyboard.as_markup(),
                    parse_mode="HTML"
                )

            # Обновляем клавиатуру водителя
            lang = await get_user_language_simple(callback.from_user.id)

            await callback.message.edit_text(
                f"🚦 <b>PODRÓŻ ROZPOCZĘTA</b>\n\n"
                f"📍 Skąd: {order.pickup_address}\n"
                f"📍 Dokąd: {order.destination_address}\n"
                f"💵 Koszt: {getattr(order, 'estimated_price', getattr(order, 'price', 0))} zł\n\n"
                f"🧭 Jedź trasą do miejsca przeznaczenia.",
                reply_markup=get_driver_ride_keyboard(lang, "in_progress"),
                parse_mode="HTML"
            )
            await callback.answer("✅ Podróż rozpoczęta")

            # Отправляем клавиатуру для навигации
            navigation_keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📍 Транслировать геопозицию", request_location=True)],
                    [KeyboardButton(text="🏁 Завершить поездку")]
                ],
                resize_keyboard=True
            )
            await callback.message.answer(
                "📍 Naciśnij przycisk poniżej, aby pasażer widział Twoją lokalizację:",
                reply_markup=navigation_keyboard
            )

    except Exception as e:
        logger.error(f"Error starting trip: {e}")
        await callback.answer("❌ Błąd podczas rozpoczynania podróży")


@driver_ride_router.callback_query(F.data == "complete_trip")
async def complete_trip(callback: CallbackQuery, state: FSMContext):
    """Завершить поездку с учетом времени ожидания"""
    try:
        ride_id = await get_current_ride_id(callback.from_user.id)

        if not ride_id:
            await callback.answer("❌ Активная поездка не найдена")
            return

        # Останавливаем активный счетчик ожидания если есть
        waiting_info = None
        if ride_id in waiting_timers:
            waiting_info = await stop_waiting_counter(ride_id)

        with Session() as session:
            order = session.query(Order).get(ride_id)
            if not order:
                await callback.answer("❌ Заказ не найден")
                return

            # Обновляем статус поездки
            order.status = "completed"
            order.completed_at = datetime.now()

            # Рассчитываем финальную стоимость
            base_price = getattr(order, 'estimated_price', getattr(order, 'price', Decimal('0')))
            if isinstance(base_price, (int, float)):
                base_price = Decimal(str(base_price))

            waiting_cost = Decimal('0')
            if waiting_info:
                waiting_cost = waiting_info['cost']

            total_price = base_price + waiting_cost

            # Обновляем финальную цену
            if hasattr(order, 'final_price'):
                order.final_price = total_price
            else:
                # Для обратной совместимости
                if hasattr(order, 'estimated_price'):
                    order.estimated_price = total_price
                elif hasattr(order, 'price'):
                    order.price = total_price

            session.commit()

            # Отправляем итоговый чек пассажиру
            client_id = getattr(order, 'client_id', getattr(order, 'user_id', None))
            if client_id:
                receipt_text = (
                    f"🏁 <b>PODRÓŻ ZAKOŃCZONA!</b>\n\n"
                    f"💵 <b>Do zapłaty:</b>\n"
                    f"- Taryfa podstawowa: {base_price} zł\n"
                )

                if waiting_cost > 0:
                    receipt_text += f"- Czas oczekiwania: {waiting_cost} zł ({waiting_info['minutes']} min)\n"

                receipt_text += (
                    f"- <b>Razem: {total_price} zł</b>\n\n"
                    f"Dziękujemy za skorzystanie z naszych usług!"
                )

                await Bots.client.send_message(
                    chat_id=client_id,
                    text=receipt_text,
                    parse_mode="HTML"
                )

            # Уведомляем водителя
            driver_text = (
                f"✅ <b>PODRÓŻ ZAKOŃCZONA</b>\n\n"
                f"💰 <b>Otrzymano:</b> {total_price} zł\n"
                f"- Podstawa: {base_price} zł\n"
            )

            if waiting_cost > 0:
                driver_text += f"- Oczekiwanie: {waiting_cost} zł\n"

            await callback.message.edit_text(
                driver_text,
                parse_mode="HTML"
            )
            await callback.answer("✅ Podróż zakończona")
            await state.clear()

            logger.info(f"Trip {ride_id} completed with total cost {total_price} zł")

    except Exception as e:
        logger.error(f"Error completing trip: {e}")
        await callback.answer("❌ Błąd podczas kończenia podróży")


# ===================================================================
# ОБРАБОТЧИК ЗАПРОСА ОСТАНОВКИ ОТ ПАССАЖИРА
# ===================================================================

async def notify_driver_stop_request(ride_id: int, passenger_id: int, language: str = "pl"):
    """Уведомление водителя о запросе остановки"""
    try:
        with Session() as session:
            order = session.query(Order).get(ride_id)
            if not order or not order.driver_id:
                return

            if language == "en":
                text = (
                    "⏸️ <b>PASSENGER REQUESTS STOP</b>\n\n"
                    f"🚖 <b>Trip ID:</b> {ride_id}\n"
                    f"👤 <b>Passenger:</b> ID {passenger_id}\n\n"
                    "⏰ <b>Waiting tariff:</b> 1 zł/minute\n\n"
                    "Choose your action:"
                )
            elif language == "ru":
                text = (
                    "⏸️ <b>ПАССАЖИР ПРОСИТ ОСТАНОВКУ</b>\n\n"
                    f"🚖 <b>ID поездки:</b> {ride_id}\n"
                    f"👤 <b>Пассажир:</b> ID {passenger_id}\n\n"
                    "⏰ <b>Тариф ожидания:</b> 1 zł/минута\n\n"
                    "Выберите действие:"
                )
            else:  # Polish
                text = (
                    "⏸️ <b>PASAŻER PROSI O ZATRZYMANIE</b>\n\n"
                    f"🚖 <b>ID podróży:</b> {ride_id}\n"
                    f"👤 <b>Pasażer:</b> ID {passenger_id}\n\n"
                    "⏰ <b>Taryfa oczekiwania:</b> 1 zł/minuta\n\n"
                    "Wybierz działanie:"
                )

            keyboard = get_driver_waiting_response_keyboard(language)

            await Bots.driver.send_message(
                chat_id=order.driver_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )

    except Exception as e:
        logger.error(f"Error notifying driver about stop request: {e}")


# Добавляем обработчик для кнопки "request_stop" если он не определен в другом месте
@driver_ride_router.callback_query(F.data == "request_stop")
async def handle_stop_request_from_passenger(callback: CallbackQuery):
    """Обработка запроса остановки от пассажира"""
    try:
        # Находим активную поездку пассажира
        with Session() as session:
            order = session.query(Order).filter(
                Order.client_id == callback.from_user.id,
                Order.status == "in_progress"
            ).order_by(Order.created_at.desc()).first()

            if not order:
                await callback.answer("❌ Активная поездка не найдена")
                return

            # Проверяем, не активен ли уже счетчик ожидания
            if order.id in waiting_timers:
                await callback.answer("⏰ Licznik oczekiwania już jest aktywny")
                return

            # Уведомляем водителя о запросе остановки
            await notify_driver_stop_request(order.id, callback.from_user.id, "pl")

            # Уведомляем пассажира
            text = (
                "⏸️ <b>Prośba o zatrzymanie wysłana!</b>\n\n"
                "⏰ <b>Taryfa oczekiwania:</b> 1 zł/minuta\n\n"
                "Czekamy na odpowiedź kierowcy..."
            )

            await callback.message.edit_text(
                text=text,
                parse_mode="HTML"
            )
            await callback.answer("✅ Prośba wysłana do kierowcy")

    except Exception as e:
        logger.error(f"Error handling stop request from passenger: {e}")
        await callback.answer("❌ Błąd podczas wysyłania prośby")


# ===================================================================
# ОБРАБОТЧИКИ НАВИГАЦИИ (БЕЗ ИЗМЕНЕНИЙ)
# ===================================================================

@driver_ride_router.callback_query(F.data == "navigate_pickup")
async def navigate_to_pickup(callback: CallbackQuery):
    """Навигация к пассажиру"""
    try:
        with Session() as session:
            order = session.query(Order).filter_by(
                driver_id=callback.from_user.id,
                status="accepted"
            ).order_by(Order.created_at.desc()).first()

            if not order:
                await callback.answer("❌ Активный заказ не найden")
                return

            # Создаем ссылку на Google Maps навигацию
            pickup_address = quote(order.pickup_address)
            google_maps_url = f"https://www.google.com/maps/dir/?api=1&destination={pickup_address}&travelmode=driving"

            await callback.message.answer(
                f"🧭 <b>Nawigacja do pasażera</b>\n\n"
                f"📍 Adres: {order.pickup_address}\n\n"
                f"[🗺️ Otwórz w Google Maps]({google_maps_url})",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            await callback.answer("🧭 Nawigacja wysłana")

    except Exception as e:
        logger.error(f"Error getting navigation: {e}")
        await callback.answer("❌ Błąd podczas pobierania nawigacji")


@driver_ride_router.callback_query(F.data == "navigate_destination")
async def navigate_to_destination(callback: CallbackQuery):
    """Навигация к месту назначения"""
    try:
        with Session() as session:
            order = session.query(Order).filter_by(
                driver_id=callback.from_user.id,
                status="in_progress"
            ).order_by(Order.created_at.desc()).first()

            if not order:
                await callback.answer("❌ Активная поездка не найдена")
                return

            # Создаем ссылку на Google Maps навигацию
            destination_address = quote(order.destination_address)
            google_maps_url = f"https://www.google.com/maps/dir/?api=1&destination={destination_address}&travelmode=driving"

            await callback.message.answer(
                f"🧭 <b>Nawigacja do miejsca przeznaczenia</b>\n\n"
                f"📍 Adres: {order.destination_address}\n\n"
                f"[🗺️ Otwórz w Google Maps]({google_maps_url})",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            await callback.answer("🧭 Nawigacja wysłana")

    except Exception as e:
        logger.error(f"Error getting destination navigation: {e}")
        await callback.answer("❌ Błąd podczas pobierania nawigacji")


# ===================================================================
# ОБРАБОТЧИКИ СВЯЗИ С ПАССАЖИРОМ (БЕЗ ИЗМЕНЕНИЙ)
# ===================================================================

@driver_ride_router.callback_query(F.data == "call_passenger")
async def call_passenger(callback: CallbackQuery):
    """Связаться с пассажиром"""
    await callback.answer(
        "📞 Funkcja dzwonienia zostanie wkrótce dodana",
        show_alert=True
    )


@driver_ride_router.callback_query(F.data == "driver_cancel")
async def driver_cancel_order(callback: CallbackQuery):
    """Отмена заказа водителем"""
    try:
        ride_id = await get_current_ride_id(callback.from_user.id)

        if not ride_id:
            await callback.answer("❌ Активный заказ не найден")
            return

        # Останавливаем счетчик ожидания если активен
        if ride_id in waiting_timers:
            await stop_waiting_counter(ride_id)

        with Session() as session:
            order = session.query(Order).get(ride_id)
            if not order:
                await callback.answer("❌ Заказ не найден")
                return

            order.status = "cancelled"
            order.cancellation_reason = "Cancelled by driver"
            order.cancelled_at = datetime.now()
            session.commit()

            # Уведомляем пассажира
            client_id = getattr(order, 'client_id', getattr(order, 'user_id', None))
            if client_id:
                await Bots.client.send_message(
                    chat_id=client_id,
                    text=(
                        "❌ <b>Kierowca anulował zamówienie</b>\n\n"
                        "Przepraszamy za niedogodność. Możesz złożyć nowe zamówienie."
                    ),
                    parse_mode="HTML"
                )

            await callback.message.edit_text(
                "❌ <b>ZAMÓWIENIE ANULOWANE</b>\n\n"
                "Anulowałeś zamówienie. Pasażer został powiadomiony.",
                parse_mode="HTML"
            )
            await callback.answer("✅ Zamówienie anulowane")

    except Exception as e:
        logger.error(f"Error cancelling order by driver: {e}")
        await callback.answer("❌ Błąd podczas anulowania")


@driver_ride_router.callback_query(F.data == "emergency_stop")
async def emergency_stop(callback: CallbackQuery):
    """Экстренная остановка"""
    try:
        ride_id = await get_current_ride_id(callback.from_user.id)

        if not ride_id:
            await callback.answer("❌ Активная поездка не найдена")
            return

        with Session() as session:
            order = session.query(Order).get(ride_id)
            if not order:
                return

            # Уведомляем пассажира
            client_id = getattr(order, 'client_id', getattr(order, 'user_id', None))
            if client_id:
                await Bots.client.send_message(
                    chat_id=client_id,
                    text=(
                        "🛑 <b>Nagłe zatrzymanie</b>\n\n"
                        "Kierowca musiał zatrzymać się z powodu sytuacji nadzwyczajnej.\n"
                        "Skontaktuj się z kierowcą w celu uzyskania szczegółów."
                    ),
                    parse_mode="HTML"
                )

            await callback.answer("🛑 Pasażer powiadomiony o nagłym zatrzymaniu")

    except Exception as e:
        logger.error(f"Error emergency stop: {e}")
        await callback.answer("❌ Błąd podczas powiadomienia")


# ===================================================================
# ОБРАБОТЧИКИ ГЕОПОЗИЦИИ И ТЕКСТОВЫХ СООБЩЕНИЙ
# ===================================================================

@driver_ride_router.message(F.location)
async def handle_driver_location_updates(message: Message):
    """Обработка обновлений местоположения водителя"""
    try:
        with Session() as session:
            # Находим активный заказ водителя
            order = session.query(Order).filter_by(
                driver_id=message.from_user.id
            ).filter(Order.status.in_(["accepted", "driver_arrived", "in_progress"])).order_by(
                Order.created_at.desc()).first()

            if not order:
                await message.answer("ℹ️ Brak aktywnych zamówień do śledzenia")
                return

            # Обновляем местоположение водителя в базе (если нужно)
            from core.models import Vehicle as DriverVehicle
            vehicle = session.query(DriverVehicle).filter_by(driver_id=message.from_user.id).first()
            if vehicle and hasattr(vehicle, 'last_lat'):
                vehicle.last_lat = message.location.latitude
                vehicle.last_lon = message.location.longitude
                session.commit()

            # Отправляем местоположение пассажиру
            client_id = getattr(order, 'client_id', getattr(order, 'user_id', None))
            if client_id:
                await Bots.client.send_location(
                    chat_id=client_id,
                    latitude=message.location.latitude,
                    longitude=message.location.longitude,
                    disable_notification=True
                )

                # Статус обновления в зависимости от стадии поездки
                if order.status == "accepted":
                    status_text = "🚗 Kierowca jedzie do Ciebie"
                elif order.status == "driver_arrived":
                    status_text = "✅ Kierowca czeka na miejscu"
                else:  # in_progress
                    status_text = "🚦 Podróż w toku"

                await Bots.client.send_message(
                    chat_id=client_id,
                    text=f"📍 {status_text}",
                    disable_notification=True
                )

            await message.answer("✅ Lokalizacja zaktualizowana", disable_notification=True)

    except Exception as e:
        logger.error(f"Error handling location update: {e}")
        await message.answer("❌ Błąd podczas aktualizacji lokalizacji")


@driver_ride_router.message(F.text == "🏁 Завершить поездку")
async def complete_trip_button(message: Message):
    """Завершить поездку через кнопку"""
    try:
        ride_id = await get_current_ride_id(message.from_user.id)

        if not ride_id:
            await message.answer("❌ Активная поездка не найдена")
            return

        with Session() as session:
            order = session.query(Order).get(ride_id)
            if not order:
                await message.answer("❌ Заказ не найден")
                return

            # Рассчитываем предварительную стоимость с учетом ожидания
            base_price = getattr(order, 'estimated_price', getattr(order, 'price', 0))
            waiting_cost = Decimal('0')
            waiting_text = ""

            if ride_id in waiting_timers:
                start_time = waiting_timers[ride_id]['start_time']
                current_time = datetime.now()
                elapsed = current_time - start_time
                minutes = max(1, int(elapsed.total_seconds() / 60))
                waiting_cost = Decimal(str(minutes))
                waiting_text = f"\n- Oczekiwanie: {waiting_cost} zł ({minutes} min)"

            total_price = (Decimal(str(base_price)) if isinstance(base_price, (int, float)) else base_price) + waiting_cost

            # Запрашиваем подтверждение
            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Tak, zakończ", callback_data="complete_trip")
            builder.button(text="❌ Anuluj", callback_data="cancel_complete")

            await message.answer(
                f"🏁 <b>Zakończyć podróż?</b>\n\n"
                f"📍 Skąd: {order.pickup_address}\n"
                f"📍 Dokąd: {order.destination_address}\n\n"
                f"💵 <b>Koszt:</b>\n"
                f"- Podstawa: {base_price} zł{waiting_text}\n"
                f"- <b>Razem: {total_price} zł</b>\n\n"
                f"Potwierdź zakończenie podróży:",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error requesting trip completion: {e}")
        await message.answer("❌ Błąd podczas przetwarzania")


@driver_ride_router.callback_query(F.data == "cancel_complete")
async def cancel_complete_trip(callback: CallbackQuery):
    """Отмена завершения поездки"""
    await callback.message.delete()
    await callback.answer("❌ Anulowano")


@driver_ride_router.message(F.text == "🛑 Остановить трансляцию")
async def stop_location_sharing(message: Message):
    """Остановить трансляцию геопозиции"""
    from aiogram.types import ReplyKeyboardRemove
    await message.answer(
        "🛑 Transmisja lokalizacji zatrzymana",
        reply_markup=ReplyKeyboardRemove()
    )


# ===================================================================
# ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ И ОБРАБОТЧИКИ
# ===================================================================

class RideStatusManager:
    """Менеджер статусов поездок"""

    @staticmethod
    def get_status_text(status: str, language: str = "pl") -> str:
        """Получить текст статуса на нужном языке"""
        status_texts = {
            "pending": {
                "pl": "⏳ Oczekuje na kierowcę",
                "en": "⏳ Waiting for driver",
                "ru": "⏳ Ожидание водителя"
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
# КОМАНДЫ ДЛЯ ОТЛАДКИ И ТЕСТИРОВАНИЯ
# ===================================================================

@driver_ride_router.message(F.text.startswith("/driver_status"))
async def check_driver_status(message: Message):
    """Команда для проверки статуса водителя"""
    from config import Config

    if str(message.from_user.id) not in Config.DRIVER_IDS:
        return

    try:
        ride_id = await get_current_ride_id(message.from_user.id)

        if not ride_id:
            await message.answer("📊 <b>STATUS KIEROWCY</b>\n\n❌ Brak aktywnych zamówień", parse_mode="HTML")
            return

        with Session() as session:
            order = session.query(Order).get(ride_id)
            if not order:
                await message.answer("❌ Zamówienie nie znalezione")
                return

            status_manager = RideStatusManager()
            status_text = status_manager.get_status_text(order.status, "pl")

            result_text = (
                f"📊 <b>STATUS KIEROWCY</b>\n\n"
                f"🆔 <b>Zamówienie:</b> #{order.id}\n"
                f"📋 <b>Status:</b> {status_text}\n"
                f"📍 <b>Skąd:</b> {order.pickup_address}\n"
                f"📍 <b>Dokąd:</b> {order.destination_address}\n"
                f"👥 <b>Pasażerów:</b> {getattr(order, 'passengers_count', 1)}\n"
                f"💵 <b>Koszt:</b> {getattr(order, 'estimated_price', getattr(order, 'price', 0))} zł\n"
                f"🕒 <b>Utworzono:</b> {order.created_at.strftime('%H:%M:%S')}"
            )

            if order.started_at:
                result_text += f"\n🚦 <b>Rozpoczęto:</b> {order.started_at.strftime('%H:%M:%S')}"

            # Информация о счетчике ожидания
            if ride_id in waiting_timers:
                start_time = waiting_timers[ride_id]['start_time']
                current_time = datetime.now()
                elapsed = current_time - start_time
                minutes = int(elapsed.total_seconds() / 60)
                result_text += f"\n⏰ <b>Oczekiwanie:</b> {minutes} min (aktywne)"

            await message.answer(result_text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Błąd sprawdzania statusu: {e}")


@driver_ride_router.message(F.text.startswith("/reset_status"))
async def reset_driver_status(message: Message):
    """Команда для сброса статуса водителя (отладка)"""
    from config import Config

    if str(message.from_user.id) not in Config.DRIVER_IDS:
        return

    try:
        # Останавливаем все активные счетчики ожидания для этого водителя
        stopped_timers = []
        for ride_id, timer_info in list(waiting_timers.items()):
            if timer_info.get('driver_id') == message.from_user.id:
                await stop_waiting_counter(ride_id)
                stopped_timers.append(ride_id)

        with Session() as session:
            # Отменяем все активные заказы водителя
            active_orders = session.query(Order).filter_by(
                driver_id=message.from_user.id
            ).filter(Order.status.in_(["accepted", "driver_arrived", "in_progress"])).all()

            cancelled_count = 0
            for order in active_orders:
                order.status = "cancelled"
                order.cancellation_reason = "Reset by driver command"
                order.cancelled_at = datetime.now()
                cancelled_count += 1

            session.commit()

            result_text = (
                f"🔄 <b>STATUS ZRESETOWANY</b>\n\n"
                f"Anulowane zamówienia: {cancelled_count}\n"
            )

            if stopped_timers:
                result_text += f"Zatrzymane liczniki: {len(stopped_timers)}\n"

            result_text += f"Status kierowcy: wolny"

            await message.answer(result_text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Błąd resetowania statusu: {e}")


# ===================================================================
# ОБРАБОТЧИКИ ТЕКУЩЕГО МЕСТОПОЛОЖЕНИЯ И ДРУГИХ CALLBACK
# ===================================================================

@driver_ride_router.callback_query(F.data == "current_location")
async def show_current_location(callback: CallbackQuery):
    """Показать текущее местоположение (для пассажира)"""
    try:
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

    except Exception as e:
        logger.error(f"Error requesting current location: {e}")
        await callback.answer("❌ Błąd podczas pobierania lokalizacji")


# ===================================================================
# АВТОМАТИЧЕСКАЯ ОЧИСТКА НЕАКТИВНЫХ СЧЕТЧИКОВ
# ===================================================================

import asyncio
from datetime import timedelta

async def cleanup_inactive_timers():
    """Автоматическая очистка неактивных счетчиков ожидания"""
    while True:
        try:
            current_time = datetime.now()
            inactive_timers = []

            for ride_id, timer_info in waiting_timers.items():
                # Если счетчик активен более 2 часов - считаем его неактивным
                if current_time - timer_info['start_time'] > timedelta(hours=2):
                    inactive_timers.append(ride_id)

            # Останавливаем неактивные счетчики
            for ride_id in inactive_timers:
                logger.warning(f"Auto-stopping inactive waiting timer for ride {ride_id}")
                await stop_waiting_counter(ride_id)

            # Проверяем каждые 30 минут
            await asyncio.sleep(1800)

        except Exception as e:
            logger.error(f"Error in cleanup_inactive_timers: {e}")
            await asyncio.sleep(1800)


# Запускаем фоновую задачу очистки при импорте модуля
import asyncio
try:
    loop = asyncio.get_event_loop()
    loop.create_task(cleanup_inactive_timers())
except RuntimeError:
    # Если event loop еще не запущен, задача будет создана позже
    pass


# ===================================================================
# СТАТИСТИКА И ОТЧЕТЫ ПО ОЖИДАНИЮ
# ===================================================================

@driver_ride_router.message(F.text.startswith("/waiting_stats"))
async def show_waiting_statistics(message: Message):
    """Показать статистику по времени ожидания"""
    from config import Config

    if str(message.from_user.id) not in Config.DRIVER_IDS:
        return

    try:
        with Session() as session:
            # Получаем все завершенные поездки водителя за последние 7 дней
            week_ago = datetime.now() - timedelta(days=7)

            orders = session.query(Order).filter(
                Order.driver_id == message.from_user.id,
                Order.status == "completed",
                Order.completed_at >= week_ago
            ).all()

            total_rides = len(orders)
            waiting_rides = 0
            total_waiting_minutes = 0
            total_waiting_cost = Decimal('0')

            for order in orders:
                if hasattr(order, 'notes') and order.notes:
                    try:
                        notes = json.loads(order.notes)
                        if isinstance(notes, dict) and 'waiting_minutes' in notes:
                            waiting_rides += 1
                            total_waiting_minutes += notes.get('waiting_minutes', 0)
                            total_waiting_cost += Decimal(str(notes.get('waiting_cost', 0)))
                    except (json.JSONDecodeError, TypeError):
                        continue

            # Статистика активных счетчиков
            active_timers = sum(1 for timer_info in waiting_timers.values()
                              if timer_info.get('driver_id') == message.from_user.id)

            stats_text = (
                f"📊 <b>STATYSTYKI OCZEKIWANIA (7 dni)</b>\n\n"
                f"🚖 <b>Łączne przejazdy:</b> {total_rides}\n"
                f"⏸️ <b>Przejazdy z oczekiwaniem:</b> {waiting_rides}\n"
                f"⏱️ <b>Łączny czas oczekiwania:</b> {total_waiting_minutes} min\n"
                f"💰 <b>Łączny zarobek z oczekiwania:</b> {total_waiting_cost} zł\n"
                f"📈 <b>Średni czas oczekiwania:</b> {total_waiting_minutes / max(waiting_rides, 1):.1f} min\n\n"
                f"🔄 <b>Aktywne liczniki:</b> {active_timers}"
            )

            await message.answer(stats_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error showing waiting statistics: {e}")
        await message.answer(f"❌ Błąd podczas pobierania statystyk: {e}")


# ===================================================================
# ЭКСПОРТ ФУНКЦИЙ ДЛЯ ИСПОЛЬЗОВАНИЯ В ДРУГИХ МОДУЛЯХ
# ===================================================================

__all__ = [
    'driver_ride_router',
    'start_waiting_counter',
    'stop_waiting_counter',
    'waiting_timers',
    'get_current_ride_id',
    'notify_driver_stop_request'
]