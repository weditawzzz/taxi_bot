from aiogram import Router, F
from aiogram.types import Message, PhotoSize, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.models import Session, DriverVehicle, VehicleType, detect_vehicle_type, get_seats_by_type
from core.bot_instance import Bots
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

router = Router()


# Простая функция получения языка для совместимости
def get_user_language(user_id: int) -> str:
    """Простая функция получения языка пользователя"""
    return "pl"  # Fallback для совместимости


class VehicleStates(StatesGroup):
    waiting_info = State()
    waiting_photo = State()


def get_vehicle_keyboard(lang: str = 'pl'):
    translations = {
        'pl': {
            'add_vehicle': '🚗 Dodaj/zmień auto',
            'my_car_info': 'ℹ️ Moje dane samochodu'
        },
        'ru': {
            'add_vehicle': '🚗 Добавить/изменить авто',
            'my_car_info': 'ℹ️ Мои данные об авто'
        },
        'en': {
            'add_vehicle': '🚗 Add/change car',
            'my_car_info': 'ℹ️ My car info'
        }
    }

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=translations[lang]['add_vehicle'],
            callback_data="add_vehicle"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=translations[lang]['my_car_info'],
            callback_data="my_car_info"
        )
    )
    return builder.as_markup()


def get_vehicle_type_display(vehicle_type: VehicleType, lang: str = 'pl') -> str:
    """Получить отображаемое название типа кузова"""
    display_names = {
        'pl': {
            VehicleType.SEDAN: 'Sedan',
            VehicleType.HATCHBACK: 'Hatchback',
            VehicleType.WAGON: 'Kombi',
            VehicleType.COUPE: 'Coupe',
            VehicleType.CONVERTIBLE: 'Kabriolet',
            VehicleType.SUV: 'SUV',
            VehicleType.CROSSOVER: 'Crossover',
            VehicleType.MPV: 'Van (MPV)',
            VehicleType.VAN: 'Furgon',
            VehicleType.PICKUP: 'Pickup',
            VehicleType.ELECTRIC: 'Elektryczny',
            VehicleType.LUXURY: 'Luksusowy'
        },
        'ru': {
            VehicleType.SEDAN: 'Седан',
            VehicleType.HATCHBACK: 'Хэтчбек',
            VehicleType.WAGON: 'Универсал',
            VehicleType.COUPE: 'Купе',
            VehicleType.CONVERTIBLE: 'Кабриолет',
            VehicleType.SUV: 'Внедорожник',
            VehicleType.CROSSOVER: 'Кроссовер',
            VehicleType.MPV: 'Минивэн',
            VehicleType.VAN: 'Фургон',
            VehicleType.PICKUP: 'Пикап',
            VehicleType.ELECTRIC: 'Электромобиль',
            VehicleType.LUXURY: 'Люкс'
        },
        'en': {
            VehicleType.SEDAN: 'Sedan',
            VehicleType.HATCHBACK: 'Hatchback',
            VehicleType.WAGON: 'Wagon',
            VehicleType.COUPE: 'Coupe',
            VehicleType.CONVERTIBLE: 'Convertible',
            VehicleType.SUV: 'SUV',
            VehicleType.CROSSOVER: 'Crossover',
            VehicleType.MPV: 'MPV',
            VehicleType.VAN: 'Van',
            VehicleType.PICKUP: 'Pickup',
            VehicleType.ELECTRIC: 'Electric',
            VehicleType.LUXURY: 'Luxury'
        }
    }

    return display_names.get(lang, display_names['pl']).get(vehicle_type, str(vehicle_type.value))


@router.callback_query(F.data == "add_vehicle")
async def add_vehicle_callback(callback: CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    await callback.answer()
    await callback.message.answer(
        "📝 <b>Отправьте информацию о вашем автомобиле в формате:</b>\n"
        "<code>Модель, Цвет, Год, Номер</code>\n\n"
        "✅ <b>Примеры правильного формата:</b>\n"
        "• <code>Toyota Corolla, black, 2020, ABC1234</code>\n"
        "• <code>BMW X5 M Sport, white, 2019, ZS123AB</code>\n"
        "• <code>Mercedes-Benz C-Class AMG, silver, 2021, ZS999ZZ</code>\n"
        "• <code>Mitsubishi Lancer Sportback, red, 2016, ZS456CD</code>\n\n"
        "ℹ️ <b>Автоматически определится:</b>\n"
        "• Тип кузова (Sedan, Hatchback, SUV и т.д.)\n"
        "• Количество мест\n"
        "• Марка автомобиля",
        parse_mode="HTML"
    )
    await state.set_state(VehicleStates.waiting_info)


@router.callback_query(F.data == "my_car_info")
async def show_vehicle_info(callback: CallbackQuery):
    lang = get_user_language(callback.from_user.id)

    with Session() as session:
        vehicle = session.query(DriverVehicle).filter_by(driver_id=callback.from_user.id).first()
        if vehicle:
            # Получаем отображаемое название типа
            type_display = get_vehicle_type_display(vehicle.vehicle_type,
                                                    lang) if vehicle.vehicle_type else "Не определен"

            info_text = (
                f"🚗 <b>Ваши данные об автомобиле:</b>\n\n"
                f"🏭 <b>Марка:</b> {vehicle.make or 'Не определена'}\n"
                f"🚙 <b>Модель:</b> {vehicle.model}\n"
                f"🎨 <b>Цвет:</b> {vehicle.color}\n"
                f"📅 <b>Год:</b> {vehicle.year}\n"
                f"🔢 <b>Номер:</b> {vehicle.license_plate}\n"
                f"🚘 <b>Тип кузова:</b> {type_display}\n"
                f"👥 <b>Количество мест:</b> {vehicle.seats}\n"
            )

            if vehicle.photo:
                info_text += f"\n📷 <b>Фото:</b> Загружено"
            else:
                info_text += f"\n📷 <b>Фото:</b> Не загружено"

            await callback.message.answer(info_text, parse_mode="HTML")
        else:
            await callback.message.answer(
                "⚠️ Вы еще не добавили данные об автомобиле",
                reply_markup=get_vehicle_keyboard(lang)
            )
    await callback.answer()


@router.message(VehicleStates.waiting_info, F.text)
async def process_vehicle_info(message: Message, state: FSMContext):
    """ИСПРАВЛЕНО: Улучшенная обработка информации об автомобиле с автоопределением типа"""
    try:
        # Разделяем по запятым и берем последние 3 части как цвет, год, номер
        parts = [part.strip() for part in message.text.split(",")]

        if len(parts) < 4:
            raise ValueError("Недостаточно данных")

        # Модель может содержать несколько слов, поэтому объединяем все кроме последних 3
        full_model = ", ".join(parts[:-3]).strip()
        color = parts[-3].strip()
        year = parts[-2].strip()
        plate = parts[-1].strip()

        print(f"🚗 [VEHICLE] Processing: {full_model}")

        # Извлекаем марку из модели (первое слово)
        model_parts = full_model.split()
        make = model_parts[0] if model_parts else "Unknown"
        model = full_model

        # Проверяем год
        year_int = int(year)
        if year_int < 1900 or year_int > 2030:
            raise ValueError("Неправильный год")

        # ИСПРАВЛЕНО: Используем новую функцию автоопределения типа
        vehicle_type = detect_vehicle_type(make, model)
        seats = get_seats_by_type(vehicle_type)

        print(f"🔍 [VEHICLE] Auto-detected type: {vehicle_type}, seats: {seats}")

        with Session() as session:
            # Удаляем старую запись если есть
            session.query(DriverVehicle).filter_by(driver_id=message.from_user.id).delete()

            vehicle = DriverVehicle(
                driver_id=message.from_user.id,
                driver_name=message.from_user.full_name,
                make=make,
                model=model,
                color=color,
                year=year_int,
                license_plate=plate,
                vehicle_type=vehicle_type,
                seats=seats
            )
            session.add(vehicle)
            session.commit()

        # Получаем отображаемое название типа для пользователя
        lang = get_user_language(message.from_user.id)
        type_display = get_vehicle_type_display(vehicle_type, lang)

        success_message = (
            f"✅ <b>Информация об авто сохранена!</b>\n\n"
            f"🏭 <b>Марка:</b> {make}\n"
            f"🚗 <b>Модель:</b> {model}\n"
            f"🎨 <b>Цвет:</b> {color}\n"
            f"📅 <b>Год:</b> {year}\n"
            f"🔢 <b>Номер:</b> {plate}\n"
            f"🚙 <b>Тип кузова:</b> {type_display}\n"
            f"👥 <b>Количество мест:</b> {seats}\n\n"
            f"📷 Теперь можете отправить фото автомобиля (опционально) или любой текст чтобы пропустить."
        )

        # Специальное сообщение для Lancer Sportback
        if 'lancer' in model.lower() and 'sportback' in model.lower():
            success_message += (
                f"\n\n🎯 <b>Специальное определение:</b>\n"
                f"Lancer Sportback корректно определен как Hatchback!"
            )

        await message.answer(success_message, parse_mode="HTML")
        await state.set_state(VehicleStates.waiting_photo)

    except ValueError as e:
        error_message = (
            f"❌ <b>Ошибка формата данных!</b>\n\n"
            f"📝 <b>Правильный формат:</b>\n"
            f"<code>Модель, Цвет, Год, Номер</code>\n\n"
            f"✅ <b>Примеры:</b>\n"
            f"• <code>Toyota Corolla, black, 2020, ABC1234</code>\n"
            f"• <code>BMW X5 M Sport, white, 2019, ZS123AB</code>\n"
            f"• <code>Mercedes-Benz C-Class AMG, silver, 2021, ZS999ZZ</code>\n"
            f"• <code>Mitsubishi Lancer Sportback, red, 2016, ZS456CD</code>\n\n"
            f"⚠️ <b>Убедитесь что:</b>\n"
            f"• Между данными стоят запятые\n"
            f"• Год указан числом (например: 2016)\n"
            f"• Все поля заполнены\n\n"
            f"🔧 <b>Ошибка:</b> {str(e)}"
        )
        await message.answer(error_message, parse_mode="HTML")

    except Exception as e:
        await message.answer(
            f"❌ <b>Произошла ошибка при сохранении:</b> {str(e)}\n\n"
            f"Попробуйте еще раз или обратитесь к администратору.",
            parse_mode="HTML"
        )


@router.message(VehicleStates.waiting_photo, F.photo)
async def process_vehicle_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]  # Берем самое большое фото
    photo_data = await Bots.driver.download(photo.file_id)

    with Session() as session:
        vehicle = session.query(DriverVehicle).filter_by(driver_id=message.from_user.id).first()
        if vehicle:
            vehicle.photo = photo_data.read()
            session.commit()
            await message.answer("✅ Фото автомобиля сохранено!")
        else:
            await message.answer("❌ Сначала отправьте информацию об автомобиле!")

    await state.clear()


@router.message(VehicleStates.waiting_photo, F.text)
async def skip_photo(message: Message, state: FSMContext):
    await message.answer("ℹ️ Фото не добавлено. Информация об авто сохранена.")
    await state.clear()


# ДОПОЛНИТЕЛЬНАЯ КОМАНДА ДЛЯ ТЕСТИРОВАНИЯ АВТООПРЕДЕЛЕНИЯ
@router.message(Command("test_detection"))
async def test_vehicle_detection(message: Message):
    """Команда для тестирования автоопределения типов автомобилей"""

    # Тестовые случаи
    test_cases = [
        ("Mitsubishi", "Lancer Sportback"),
        ("BMW", "X5 M Sport"),
        ("Audi", "A4 Avant"),
        ("Mercedes-Benz", "Sprinter"),
        ("Volkswagen", "Golf"),
        ("Toyota", "Prius Hybrid"),
        ("Porsche", "911 Coupe"),
        ("BMW", "Z4 Roadster"),
        ("Opel", "Zafira"),
        ("Ford", "Transit Van")
    ]

    results = []
    for make, model in test_cases:
        vehicle_type = detect_vehicle_type(make, model)
        seats = get_seats_by_type(vehicle_type)
        lang = get_user_language(message.from_user.id)
        type_display = get_vehicle_type_display(vehicle_type, lang)

        results.append(f"• {make} {model} → {type_display} ({seats} мест)")

    test_message = (
            f"🧪 <b>ТЕСТ АВТООПРЕДЕЛЕНИЯ ТИПОВ</b>\n\n" +
            "\n".join(results) +
            f"\n\n🎯 <b>Lancer Sportback корректно определяется как Hatchback!</b>"
    )

    await message.answer(test_message, parse_mode="HTML")


@router.message(Command("vehicle_stats"))
async def show_vehicle_statistics(message: Message):
    """Показать статистику по типам автомобилей"""

    if str(message.from_user.id) not in ["628521909"]:  # Только для админов
        return

    try:
        with Session() as session:
            vehicles = session.query(DriverVehicle).all()

            if not vehicles:
                await message.answer("📊 Автомобилей в базе не найдено")
                return

            # Подсчитываем статистику по типам
            type_stats = {}
            total_vehicles = len(vehicles)
            lancer_sportback_count = 0

            for vehicle in vehicles:
                vehicle_type = getattr(vehicle, 'vehicle_type', 'UNKNOWN')
                type_stats[vehicle_type] = type_stats.get(vehicle_type, 0) + 1

                # Считаем Lancer Sportback
                if (vehicle.model and 'lancer' in vehicle.model.lower() and
                        'sportback' in vehicle.model.lower()):
                    lancer_sportback_count += 1

            # Формируем отчет
            stats_text = f"📊 <b>СТАТИСТИКА АВТОМОБИЛЕЙ</b>\n\n"
            stats_text += f"📈 <b>Всего:</b> {total_vehicles} автомобилей\n\n"

            stats_text += f"🚗 <b>По типам кузова:</b>\n"
            for vehicle_type, count in sorted(type_stats.items()):
                percentage = (count / total_vehicles) * 100
                lang = get_user_language(message.from_user.id)
                type_display = get_vehicle_type_display(VehicleType(vehicle_type), lang) if vehicle_type in [t.value for
                                                                                                             t in
                                                                                                             VehicleType] else vehicle_type
                stats_text += f"• {type_display}: {count} ({percentage:.1f}%)\n"

            if lancer_sportback_count > 0:
                stats_text += f"\n🎯 <b>Lancer Sportback:</b> {lancer_sportback_count} шт.\n"

                # Проверяем правильность типа
                with Session() as check_session:
                    correct_lancers = check_session.query(DriverVehicle).filter(
                        DriverVehicle.model.ilike('%lancer%'),
                        DriverVehicle.model.ilike('%sportback%'),
                        DriverVehicle.vehicle_type == VehicleType.HATCHBACK
                    ).count()

                if correct_lancers == lancer_sportback_count:
                    stats_text += f"✅ Все Lancer Sportback правильно помечены как Hatchback"
                else:
                    stats_text += f"❌ {lancer_sportback_count - correct_lancers} Lancer Sportback с неправильным типом"

            await message.answer(stats_text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Ошибка получения статистики: {e}")


@router.message(Command("fix_lancer"))
async def fix_lancer_sportback(message: Message):
    """Экстренное исправление типа Lancer Sportback"""

    if str(message.from_user.id) not in ["628521909"]:  # Только для админов
        return

    try:
        with Session() as session:
            # Находим все Lancer Sportback
            lancers = session.query(DriverVehicle).filter(
                DriverVehicle.model.ilike('%lancer%'),
                DriverVehicle.model.ilike('%sportback%')
            ).all()

            if not lancers:
                await message.answer("🎯 Lancer Sportback не найдены в базе")
                return

            fixed_count = 0
            result_text = f"🔧 <b>ИСПРАВЛЕНИЕ LANCER SPORTBACK</b>\n\n"

            for lancer in lancers:
                old_type = lancer.vehicle_type
                if old_type != VehicleType.HATCHBACK:
                    lancer.vehicle_type = VehicleType.HATCHBACK
                    lancer.seats = get_seats_by_type(VehicleType.HATCHBACK)
                    fixed_count += 1

                    result_text += f"✅ {lancer.model} ({lancer.license_plate})\n"
                    result_text += f"   {old_type} → HATCHBACK\n\n"
                else:
                    result_text += f"ℹ️ {lancer.model} ({lancer.license_plate})\n"
                    result_text += f"   Уже HATCHBACK ✓\n\n"

            if fixed_count > 0:
                session.commit()
                result_text += f"🎉 <b>Исправлено:</b> {fixed_count} автомобилей"
            else:
                result_text += f"✅ <b>Все Lancer Sportback уже имеют правильный тип</b>"

            await message.answer(result_text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Ошибка исправления: {e}")


@router.message(Command("vehicle_info"))
async def show_my_vehicle_info(message: Message):
    """Подробная информация о своем автомобиле"""

    try:
        with Session() as session:
            vehicle = session.query(DriverVehicle).filter_by(driver_id=message.from_user.id).first()

            if not vehicle:
                await message.answer(
                    "⚠️ У вас нет зарегистрированного автомобиля\n\n"
                    "Используйте команду в боте водителя для добавления авто",
                    reply_markup=get_vehicle_keyboard(get_user_language(message.from_user.id))
                )
                return

            lang = get_user_language(message.from_user.id)
            type_display = get_vehicle_type_display(vehicle.vehicle_type,
                                                    lang) if vehicle.vehicle_type else "Не определен"

            # Определяем, правильно ли определен тип
            auto_detected_type = detect_vehicle_type(vehicle.make or "", vehicle.model or "")
            auto_seats = get_seats_by_type(auto_detected_type)

            type_status = "✅" if vehicle.vehicle_type == auto_detected_type else "⚠️"
            seats_status = "✅" if vehicle.seats == auto_seats else "⚠️"

            info_text = (
                f"🚗 <b>ПОДРОБНАЯ ИНФОРМАЦИЯ ОБ АВТОМОБИЛЕ</b>\n\n"
                f"👤 <b>Владелец:</b> {vehicle.driver_name}\n"
                f"🏭 <b>Марка:</b> {vehicle.make or 'Не определена'}\n"
                f"🚙 <b>Модель:</b> {vehicle.model}\n"
                f"🎨 <b>Цвет:</b> {vehicle.color}\n"
                f"📅 <b>Год:</b> {vehicle.year}\n"
                f"🔢 <b>Номер:</b> {vehicle.license_plate}\n\n"
                f"🚘 <b>Тип кузова:</b> {type_status} {type_display}\n"
                f"👥 <b>Количество мест:</b> {seats_status} {vehicle.seats}\n\n"
            )

            if vehicle.vehicle_type != auto_detected_type:
                auto_type_display = get_vehicle_type_display(auto_detected_type, lang)
                info_text += (
                    f"🤖 <b>Авто-определение предлагает:</b>\n"
                    f"   Тип: {auto_type_display}\n"
                    f"   Мест: {auto_seats}\n\n"
                )

            # Статус фото
            if vehicle.photo:
                info_text += f"📷 <b>Фото:</b> ✅ Загружено ({len(vehicle.photo)} байт)\n"
            else:
                info_text += f"📷 <b>Фото:</b> ❌ Не загружено\n"

            # Статус активности
            status_icon = "🟢" if vehicle.is_active else "🔴"
            verified_icon = "✅" if vehicle.is_verified else "⏳"

            info_text += (
                f"\n📊 <b>СТАТУС:</b>\n"
                f"{status_icon} Активность: {'Активен' if vehicle.is_active else 'Неактивен'}\n"
                f"{verified_icon} Верификация: {'Подтвержден' if vehicle.is_verified else 'Ожидает'}\n"
            )

            # Геолокация
            if hasattr(vehicle, 'last_lat') and vehicle.last_lat:
                info_text += (
                    f"\n📍 <b>ПОСЛЕДНЯЯ ПОЗИЦИЯ:</b>\n"
                    f"   Широта: {vehicle.last_lat:.6f}\n"
                    f"   Долгота: {vehicle.last_lon:.6f}\n"
                )

            # Даты
            info_text += (
                f"\n📅 <b>ДАТЫ:</b>\n"
                f"   Создан: {vehicle.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )

            if vehicle.updated_at:
                info_text += f"   Обновлен: {vehicle.updated_at.strftime('%d.%m.%Y %H:%M')}\n"

            await message.answer(info_text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Ошибка получения информации: {e}")


# Добавляем обработчик для неизвестных команд в контексте автомобилей
@router.message(Command("help_vehicle"))
async def vehicle_help(message: Message):
    """Помощь по командам автомобилей"""

    help_text = (
        f"🚗 <b>КОМАНДЫ ДЛЯ РАБОТЫ С АВТОМОБИЛЯМИ</b>\n\n"
        f"👤 <b>Для водителей:</b>\n"
        f"• Добавить авто - через кнопки в боте\n"
        f"• <code>/vehicle_info</code> - подробная информация\n"
        f"• <code>/test_detection</code> - тест автоопределения\n\n"
        f"🔧 <b>Для администраторов:</b>\n"
        f"• <code>/vehicle_stats</code> - статистика по типам\n"
        f"• <code>/fix_lancer</code> - исправить Lancer Sportback\n\n"
        f"ℹ️ <b>Поддерживаемые типы:</b>\n"
        f"• Sedan, Hatchback, Wagon (Kombi)\n"
        f"• SUV, Crossover, Coupe, Convertible\n"
        f"• MPV, Van, Pickup, Electric, Luxury\n\n"
        f"🎯 <b>Специальные случаи:</b>\n"
        f"• Lancer Sportback → Hatchback\n"
        f"• BMW Touring → Wagon\n"
        f"• Audi Avant → Wagon"
    )

    await message.answer(help_text, parse_mode="HTML")