# Обновите notifications.py

"""
Сервис уведомлений для водителей и клиентов
"""
import logging
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import Config

logger = logging.getLogger(__name__)


async def notify_driver_about_ride(ride_id: int, ride_data: dict):
    """Уведомление водителя о новой поездке - ИСПОЛЬЗУЕМ НОВЫЙ СЕРВИС"""
    try:
        from core.services.driver_notification import driver_notification_service

        # Используем новый сервис множественных уведомлений
        await driver_notification_service.notify_all_drivers(ride_id, ride_data)

        logger.info(f"All drivers notified about ride {ride_id} via new service")

    except Exception as e:
        logger.error(f"Error notifying drivers about ride {ride_id}: {e}")


async def notify_client_order_update(user_id: int, message: str):
    """Уведомление клиента об обновлении заказа с МАКСИМАЛЬНЫМ звуком"""
    try:
        from core.bot_instance import Bots

        # МАКСИМАЛЬНЫЕ НАСТРОЙКИ ДЛЯ ЗВУКА
        await Bots.client.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="HTML",
            disable_notification=False,    # Включаем уведомления
            protect_content=False,         # Не защищаем контент
            disable_web_page_preview=True, # Отключаем превью
            message_thread_id=None         # Основная ветка чата
        )

        # Дополнительно отправляем эмодзи для привлечения внимания
        try:
            await Bots.client.send_message(
                chat_id=user_id,
                text="🔔",  # Колокольчик
                disable_notification=False
            )
        except:
            pass  # Игнорируем ошибки

        logger.info(f"Client {user_id} notified with maximum sound settings")

    except Exception as e:
        logger.error(f"Error notifying client {user_id}: {e}")


async def send_sound_notification(chat_id: int, text: str, bot_instance):
    """Универсальная функция отправки звукового уведомления"""
    try:
        # Основное сообщение с максимальными настройками звука
        await bot_instance.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            disable_notification=False,
            protect_content=False,
            disable_web_page_preview=True
        )

        # Дополнительный звуковой эффект через стикер
        try:
            # Стикер-звонок (если доступен)
            await bot_instance.send_sticker(
                chat_id=chat_id,
                sticker="CAACAgIAAxkBAAEMxjJnQVT6R1q-gk0pF9J2AAHfgWG3BgACJgADKA9qFIxUTmr_Zm9lHgQ",
                disable_notification=False
            )
        except:
            # Если стикер недоступен, отправляем аудио-сообщение с тональным сигналом
            try:
                await bot_instance.send_message(
                    chat_id=chat_id,
                    text="🔊 NOWE ZAMÓWIENIE! 🔊",
                    disable_notification=False
                )
            except:
                pass

    except Exception as e:
        logger.error(f"Error sending sound notification: {e}")


# Обратная совместимость со старыми функциями
async def notify_driver(order_id: int):
    """Обратная совместимость - перенаправляем на новую функцию"""
    # Создаем фиктивные данные для совместимости
    ride_data = {
        'destination_address': 'Unknown',
        'distance_km': 5.0,
        'estimated_price': 50.0,
        'notes': 'Legacy order'
    }
    await notify_driver_about_ride(order_id, ride_data)