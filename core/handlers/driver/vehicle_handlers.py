from aiogram import Router, F
from aiogram.types import Message, PhotoSize, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.models import Session, DriverVehicle
from core.bot_instance import Bots
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from core.services.user_service import get_user_language
from config import Config

router = Router()


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

@router.callback_query(F.data == "add_vehicle")
async def add_vehicle_callback(callback: CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    await callback.answer()
    await callback.message.answer(
        "Отправьте информацию о вашем автомобиле в формате:\n"
        "Модель, Цвет, Год, Номер\n\n"
        "Пример:\n"
        "Lexus RX, black, 2024, ZS111ZS"
    )
    await state.set_state(VehicleStates.waiting_info)

@router.callback_query(F.data == "my_car_info")
async def show_vehicle_info(callback: CallbackQuery):
    with Session() as session:
        vehicle = session.query(DriverVehicle).filter_by(driver_id=callback.from_user.id).first()
        if vehicle:
            await callback.message.answer(
                f"Ваши данные об автомобиле:\n\n"
                f"Модель: {vehicle.model}\n"
                f"Цвет: {vehicle.color}\n"
                f"Год: {vehicle.year}\n"
                f"Номер: {vehicle.license_plate}"
            )
        else:
            await callback.message.answer(
                "Вы еще не добавили данные об автомобиле",
                reply_markup=get_vehicle_keyboard(get_user_language(callback.from_user.id))
            )
    await callback.answer()

@router.message(VehicleStates.waiting_info, F.text)
async def process_vehicle_info(message: Message, state: FSMContext):
    try:
        model, color, year, plate = map(str.strip, message.text.split(","))

        with Session() as session:
            # Удаляем старую запись если есть
            session.query(DriverVehicle).filter_by(driver_id=message.from_user.id).delete()

            vehicle = DriverVehicle(
                driver_id=message.from_user.id,
                driver_name=message.from_user.full_name,
                model=model,
                color=color,
                year=int(year),
                license_plate=plate
            )
            session.add(vehicle)
            session.commit()

        await message.answer(
            "Информация об авто сохранена!\n"
            "Теперь можете отправить фото автомобиля (опционально)"
        )
        await state.set_state(VehicleStates.waiting_photo)
    except Exception as e:
        await message.answer(f"Ошибка формата. Пример правильного формата:\nToyota Corolla, black, 2020, ABC1234")


@router.message(VehicleStates.waiting_photo, F.photo)
async def process_vehicle_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]  # Берем самое большое фото
    photo_data = await Bots.driver.download(photo.file_id)

    with Session() as session:
        vehicle = session.query(DriverVehicle).filter_by(driver_id=message.from_user.id).first()
        if vehicle:
            vehicle.photo = photo_data.read()
            session.commit()
            await message.answer("Фото автомобиля сохранено!")
        else:
            await message.answer("Сначала отправьте информацию об автомобиле!")

    await state.clear()


@router.message(VehicleStates.waiting_photo, F.text)
async def skip_photo(message: Message, state: FSMContext):
    await message.answer("Фото не добавлено. Информация об авто сохранена.")
    await state.clear()