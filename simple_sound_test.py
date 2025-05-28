# Создайте файл: direct_sound_test.py

"""
Прямой тест звуковых уведомлений без сложной конфигурации
"""
import asyncio
from aiogram import Bot

# ВСТАВЬТЕ СЮДА ВАШИ ТОКЕНЫ И ID НАПРЯМУЮ
DRIVER_BOT_TOKEN = "8012773257:AAHuhGx8TwaEP1KPooBFAq8EfUNSRZfmJtM"
DRIVER_IDS = ['628521909','6158974369']  # Замените на реальные ID водителей


async def test_sound_directly():
    """Прямой тест звука"""

    # Создаем бот напрямую
    driver_bot = Bot(token=DRIVER_BOT_TOKEN)

    print("🧪 Тестирование звуковых уведомлений водителям...")

    for i, driver_id in enumerate(DRIVER_IDS, 1):
        try:
            print(f"\n{i}. Отправка уведомления водителю {driver_id}...")

            # Тест 1: Обычное сообщение с максимальными настройками звука
            await driver_bot.send_message(
                chat_id=int(driver_id),
                text="🔊🔊🔊 ТЕСТ ЗВУКА 🔊🔊🔊",
                disable_notification=False,
                protect_content=False
            )

            await asyncio.sleep(0.5)

            # Тест 2: Основное сообщение
            await driver_bot.send_message(
                chat_id=int(driver_id),
                text=(
                    "🔔 <b>ТЕСТ ЗВУКОВОГО УВЕДОМЛЕНИЯ</b>\n\n"
                    "Если вы получили это сообщение:\n"
                    "✅ Бот работает правильно\n"
                    "🔊 Был ли звук уведомления?\n\n"
                    "<b>Если звука НЕТ, проверьте:</b>\n"
                    "1. Настройки → Уведомления → Звук в Telegram\n"
                    "2. Громкость уведомлений на телефоне\n"
                    "3. Телефон не в беззвучном режиме\n"
                    "4. Разрешения для Telegram в настройках системы"
                ),
                parse_mode="HTML",
                disable_notification=False,
                protect_content=False
            )

            await asyncio.sleep(0.5)

            # Тест 3: Дополнительный звуковой сигнал
            await driver_bot.send_message(
                chat_id=int(driver_id),
                text="🚨 ДОПОЛНИТЕЛЬНЫЙ ЗВУКОВОЙ СИГНАЛ 🚨",
                disable_notification=False
            )

            print(f"✅ Уведомления отправлены водителю {driver_id}")

            await asyncio.sleep(2)  # Пауза между водителями

        except Exception as e:
            print(f"❌ Ошибка для водителя {driver_id}: {e}")
            print(f"   Возможно ID {driver_id} неверный или водитель не запускал бота")

    print(f"\n🏁 Тест завершен!")
    print("\n📱 ИНСТРУКЦИИ ДЛЯ ВОДИТЕЛЕЙ:")
    print("=" * 50)
    print("1. Проверьте получили ли вы 3 сообщения от бота")
    print("2. Был ли звук при получении сообщений?")
    print("\n🔧 ЕСЛИ ЗВУКА НЕТ:")
    print("• В Telegram: Настройки → Уведомления → Звук")
    print("• Найдите бота в списке чатов → Настройки чата → Звук")
    print("• Проверьте громкость уведомлений в системе")
    print("• Убедитесь что телефон не в режиме 'Не беспокоить'")
    print("• Разрешения для Telegram в настройках телефона")

    # Закрываем сессию бота
    await driver_bot.session.close()


async def test_driver_availability():
    """Проверка доступности водителей"""

    driver_bot = Bot(token=DRIVER_BOT_TOKEN)

    print("\n🔍 Проверка доступности водителей...")

    for driver_id in DRIVER_IDS:
        try:
            # Пытаемся получить информацию о чате
            chat = await driver_bot.get_chat(int(driver_id))
            print(f"✅ Водитель {driver_id}: {chat.full_name or chat.first_name}")

        except Exception as e:
            print(f"❌ Водитель {driver_id} недоступен: {str(e)}")
            if "chat not found" in str(e).lower():
                print(f"   → Водитель с ID {driver_id} не запускал бота (/start)")
            elif "bot was blocked" in str(e).lower():
                print(f"   → Водитель заблокировал бота")

    await driver_bot.session.close()


async def main():
    """Главная функция"""
    print("🚀 Запуск тестирования звуковых уведомлений...")
    print("=" * 50)

    try:
        # Сначала проверяем доступность водителей
        await test_driver_availability()

        print("\n" + "=" * 50)

        # Затем тестируем звук
        await test_sound_directly()

    except KeyboardInterrupt:
        print("\n🛑 Тестирование прервано пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())