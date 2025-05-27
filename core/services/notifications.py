"""
Сервис уведомлений для водителей и клиентов
"""
import logging
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import Config

logger = logging.getLogger(__name__)


async def notify_driver_about_ride(ride_id: int, ride_data: dict):
    """Уведомление водителя о новой поездке"""
    try:
        from core.bot_instance import Bots

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Przyjmij", callback_data=f"accept_{ride_id}")
        builder.button(text="❌ Odrzuć", callback_data=f"reject_{ride_id}")

        # Проверяем тип заказа
        if ride_data.get('notes', '').startswith('ALCOHOL DELIVERY'):
            # Заказ алкоголя БЕЗ списка магазинов

            # Извлекаем информацию из notes
            notes = ride_data.get('notes', '')
            products = "N/A"
            budget = "N/A"

            if "Products:" in notes:
                products = notes.split("Products:")[1].split(",")[0].strip()
            if "Budget:" in notes:
                budget = notes.split("Budget:")[1].split("zł")[0].strip()

            text = (
                "🛒 <b>DOSTAWA ALKOHOLU</b>\n\n"
                f"📝 <b>Lista zakupów:</b>\n{products}\n\n"
                f"💰 <b>Budżet klienta:</b> {budget} zł\n"
                f"📍 <b>Dostawa na:</b> {ride_data.get('destination_address', 'N/A')}\n"
                f"📏 <b>Odległość:</b> ~{ride_data.get('distance_km', 5):.1f} km\n"
                f"💵 <b>Twoja opłata:</b> 20 zł\n\n"
                f"ℹ️ <b>Instrukcje:</b>\n"
                f"1. Wybierz najbliższy sklep z alkoholem\n"
                f"2. Kup produkty zgodnie z listą\n"
                f"3. Zachowaj paragon fiskalny!\n"
                f"4. Dostarcz + sprawdź dokumenty (18+)\n"
                f"5. Odbierz: 20 zł + koszt zakupów"
            )
        else:
            # Обычный заказ такси
            text = (
                "🚖 <b>Nowe zamówienie!</b>\n\n"
                f"Z: {ride_data.get('pickup_address', 'N/A')}\n"
                f"Do: {ride_data.get('destination_address', 'N/A')}\n"
                f"Dystans: {ride_data.get('distance_km', 0):.1f} km\n"
                f"Cena: {ride_data.get('estimated_price', 0)} zł\n"
                f"Pasażerów: {ride_data.get('passengers_count', 1)}"
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


async def notify_client_order_update(user_id: int, message: str):
    """Уведомление клиента об обновлении заказа"""
    try:
        from core.bot_instance import Bots

        await Bots.client.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="HTML"
        )

        logger.info(f"Client {user_id} notified about order update")

    except Exception as e:
        logger.error(f"Error notifying client {user_id}: {e}")


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