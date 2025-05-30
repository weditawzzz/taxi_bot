"""
Модели базы данных с правильной типизацией и обратной совместимостью
ИСПРАВЛЕНО: Добавлены новые типы автомобилей (WAGON, COUPE, MPV и т.д.)
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, Enum as SQLEnum, DECIMAL, LargeBinary
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import create_engine


class Base(DeclarativeBase):
    """Базовая модель"""
    pass


class UserRole(str, Enum):
    """Роли пользователей"""
    CLIENT = "client"
    DRIVER = "driver"
    ADMIN = "admin"


class RideStatus(str, Enum):
    """Статусы поездок"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DRIVER_ARRIVED = "driver_arrived"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"  # Добавлено для совместимости


class VehicleType(str, Enum):
    """ИСПРАВЛЕНО: Расширенные типы транспортных средств"""
    SEDAN = "sedan"           # Седан
    HATCHBACK = "hatchback"   # Хэтчбек
    WAGON = "wagon"           # ИСПРАВЛЕНО: Универсал/комби (было ошибка)
    COUPE = "coupe"           # ДОБАВЛЕНО: Купе
    CONVERTIBLE = "convertible" # ДОБАВЛЕНО: Кабриолет
    SUV = "suv"               # Внедорожник
    CROSSOVER = "crossover"   # ДОБАВЛЕНО: Кроссовер
    MPV = "mpv"               # ДОБАВЛЕНО: Минивэн
    VAN = "van"               # Фургон
    PICKUP = "pickup"         # ДОБАВЛЕНО: Пикап
    ELECTRIC = "electric"     # ДОБАВЛЕНО: Электромобиль
    LUXURY = "luxury"         # Премиум класс


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), nullable=False, default=UserRole.CLIENT)
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="pl")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Метаданные
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Отношения
    client_rides: Mapped[List["Ride"]] = relationship("Ride", foreign_keys="Ride.client_id", back_populates="client")
    driver_rides: Mapped[List["Ride"]] = relationship("Ride", foreign_keys="Ride.driver_id", back_populates="driver")
    vehicles: Mapped[List["Vehicle"]] = relationship("Vehicle", back_populates="driver")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, role={self.role})>"


class Vehicle(Base):
    """ИСПРАВЛЕНО: Модель транспортного средства с улучшенной типизацией"""
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    driver_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Для совместимости

    # Информация о транспорте
    make: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Марка (BMW, Audi и т.д.)
    model: Mapped[str] = mapped_column(String(100), nullable=False)          # Полная модель
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str] = mapped_column(String(50), nullable=False)
    license_plate: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)

    # ИСПРАВЛЕНО: Теперь поддерживает все новые типы
    vehicle_type: Mapped[Optional[VehicleType]] = mapped_column(SQLEnum(VehicleType), nullable=True)
    seats: Mapped[int] = mapped_column(Integer, nullable=False, default=4)

    # Дополнительные поля for compatibility
    photo: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    last_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Статус
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Метаданные
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Отношения
    driver: Mapped["User"] = relationship("User", back_populates="vehicles")
    rides: Mapped[List["Ride"]] = relationship("Ride", back_populates="vehicle")

    def __repr__(self) -> str:
        return f"<Vehicle(id={self.id}, {self.make} {self.model}, plate={self.license_plate}, type={self.vehicle_type})>"


class Ride(Base):
    """Модель поездки"""
    __tablename__ = "rides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    driver_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    vehicle_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("vehicles.id"), nullable=True)

    # Для совместимости со старой системой
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Алиас для client_id
    driver_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Маршрут
    pickup_address: Mapped[str] = mapped_column(Text, nullable=False)
    pickup_lat: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_lng: Mapped[float] = mapped_column(Float, nullable=False)

    destination_address: Mapped[str] = mapped_column(Text, nullable=False)
    destination_lat: Mapped[float] = mapped_column(Float, nullable=False)
    destination_lng: Mapped[float] = mapped_column(Float, nullable=False)

    # Дополнительные поля для совместимости
    origin: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Алиас для pickup_address
    destination: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Алиас для destination_address

    # НОВЫЕ ПОЛЯ для счетчика ожидания:
    waiting_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    waiting_ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    waiting_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    waiting_cost: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2), nullable=True, default=Decimal('0.00'))

    # Дополнительные остановки (JSON список)
    stops_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON строка с историей остановок

    # Стоимость и расстояние
    distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estimated_price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    final_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2), nullable=True)
    price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2), nullable=True)  # Алиас для estimated_price

    # Статус и время
    status: Mapped[RideStatus] = mapped_column(SQLEnum(RideStatus), nullable=False, default=RideStatus.PENDING)
    passengers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Дополнительные поля для алкоголя и совместимости
    order_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "alcohol", "city", etc.
    products: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Список товаров для алкоголя
    budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Бюджет на покупки
    payment_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="cash")

    # Временные метки
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Дополнительная информация
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Отношения
    client: Mapped["User"] = relationship("User", foreign_keys=[client_id], back_populates="client_rides")
    driver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[driver_id], back_populates="driver_rides")
    vehicle: Mapped[Optional["Vehicle"]] = relationship("Vehicle", back_populates="rides")

    @property
    def duration_seconds(self) -> Optional[int]:
        """Длительность поездки в секундах"""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None

    def __repr__(self) -> str:
        return f"<Ride(id={self.id}, status={self.status}, client_id={self.client_id})>"


class DriverLocation(Base):
    """Модель для отслеживания местоположения водителя"""
    __tablename__ = "driver_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Координаты
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Статус
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Время
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())

    # Отношение
    driver: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<DriverLocation(driver_id={self.driver_id}, lat={self.latitude}, lng={self.longitude})>"


# ============================================
# АЛИАСЫ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
# ============================================

# Для старого кода, который использует DriverVehicle
DriverVehicle = Vehicle

# Для старого кода, который использует Order
Order = Ride

# ============================================
# СЕССИЯ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
# ============================================

def get_sync_session():
    """Создание синхронной сессии для обратной совместимости"""
    from core.config import config

    # Преобразуем async URL в sync URL
    sync_url = config.database.url.replace('sqlite+aiosqlite:', 'sqlite:')

    engine = create_engine(sync_url, echo=config.database.echo)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


class SessionContext:
    """Контекстный менеджер для совместимости с old Session()"""

    def __enter__(self):
        self.session = get_sync_session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
        finally:
            self.session.close()


# Алиас для старого кода: with Session() as session:
Session = SessionContext


# ============================================
# ФУНКЦИИ ДЛЯ АВТООПРЕДЕЛЕНИЯ ТИПА КУЗОВА
# ============================================

def detect_vehicle_type(make: str, model: str) -> VehicleType:
    """
    НОВАЯ ФУНКЦИЯ: Автоматическое определение типа кузова по марке и модели

    Args:
        make: Марка автомобиля (BMW, Audi и т.д.)
        model: Полная модель

    Returns:
        VehicleType: Определенный тип кузова
    """
    if not make or not model:
        return VehicleType.SEDAN

    make_lower = make.lower()
    model_lower = model.lower()
    full_name = f"{make_lower} {model_lower}"

    # Универсалы / Wagon / Комби
    wagon_keywords = [
        'touring', 'estate', 'wagon', 'kombi', 'avant', 'variant', 'sw', 'break',
        'sportwagon', 'allroad', 'outback', 'cross country'
    ]
    if any(keyword in model_lower for keyword in wagon_keywords):
        return VehicleType.WAGON

    # Внедорожники / SUV (большие)
    suv_keywords = [
        'x5', 'x7', 'q7', 'q8', 'gle', 'gls', 'cayenne', 'touareg', 'tahoe',
        'escalade', 'navigator', 'expedition', 'suburban', 'yukon', 'range rover',
        'discovery', 'defender'
    ]
    if any(keyword in model_lower for keyword in suv_keywords):
        return VehicleType.SUV

    # Кроссоверы (компактные SUV)
    crossover_keywords = [
        'x1', 'x3', 'q3', 'q5', 'glb', 'glc', 'macan', 'tiguan', 'rav4', 'cr-v',
        'qashqai', 'juke', 'captur', 'tucson', 'sportage', 'cx-5', 'forester',
        'xv', 'impreza', 'crossover', 'cross'
    ]
    if any(keyword in model_lower for keyword in crossover_keywords):
        return VehicleType.CROSSOVER

    # Фургоны / Van
    van_keywords = [
        'van', 'transporter', 'sprinter', 'ducato', 'transit', 'crafter',
        'daily', 'master', 'movano', 'boxer'
    ]
    if any(keyword in model_lower for keyword in van_keywords):
        return VehicleType.VAN

    # Минивэны / MPV
    mpv_keywords = [
        'mpv', 'zafira', 'sharan', 'galaxy', 'espace', 'scenic', 'touran',
        'verso', 'carens', 'stream', 'odyssey', 'previa'
    ]
    if any(keyword in model_lower for keyword in mpv_keywords):
        return VehicleType.MPV

    # Купе и кабриолеты
    coupe_keywords = [
        'coupe', 'coupé', 'cabrio', 'convertible', 'roadster', 'spider', 'spyder',
        'targa', 'z4', 'slk', 'slc', 'tt', 'boxster'
    ]
    if any(keyword in model_lower for keyword in coupe_keywords):
        if any(keyword in model_lower for keyword in ['cabrio', 'convertible', 'roadster', 'spider', 'spyder']):
            return VehicleType.CONVERTIBLE
        else:
            return VehicleType.COUPE

    # Хэтчбеки (включая спортбэки)
    hatchback_keywords = [
        'hatchback', 'golf', 'polo', 'corsa', 'fiesta', 'focus', 'astra', 'civic',
        'i20', 'i30', 'rio', 'ceed', 'ibiza', 'leon', 'fabia', 'swift',
        'sportback', 'back'  # ИСПРАВЛЕНО: Sportback тоже хэтчбек
    ]

    # Специальная проверка для Lancer Sportback
    if 'lancer' in model_lower and 'sportback' in model_lower:
        return VehicleType.HATCHBACK

    if any(keyword in model_lower for keyword in hatchback_keywords):
        return VehicleType.HATCHBACK

    # Пикапы
    pickup_keywords = [
        'pickup', 'pick-up', 'navara', 'hilux', 'ranger', 'amarok', 'l200',
        'frontier', 'ridgeline', 'colorado', 'canyon'
    ]
    if any(keyword in model_lower for keyword in pickup_keywords):
        return VehicleType.PICKUP

    # Электромобили
    electric_keywords = [
        'tesla', 'electric', 'hybrid', 'prius', 'leaf', 'zoe', 'e-golf',
        'i3', 'i8', 'model s', 'model 3', 'model x', 'model y'
    ]
    if any(keyword in full_name for keyword in electric_keywords):
        return VehicleType.ELECTRIC

    # Премиум марки (люкс)
    luxury_makes = [
        'mercedes', 'bmw', 'audi', 'lexus', 'jaguar', 'porsche', 'bentley',
        'rolls-royce', 'maserati', 'ferrari', 'lamborghini', 'aston martin'
    ]

    # Премиум модели
    luxury_models = [
        's-class', 'e-class', '7 series', 'a8', 'ls', 'xj', 'panamera',
        'quattroporte', 'continental', 'phantom', 'ghost'
    ]

    if (make_lower in luxury_makes and any(keyword in model_lower for keyword in luxury_models)) or \
       any(keyword in full_name for keyword in ['s-class', 'phantom', 'continental gt']):
        return VehicleType.LUXURY

    # По умолчанию - седан
    return VehicleType.SEDAN


def get_seats_by_type(vehicle_type: VehicleType) -> int:
    """
    НОВАЯ ФУНКЦИЯ: Определение количества мест по типу кузова

    Args:
        vehicle_type: Тип кузова

    Returns:
        int: Количество мест
    """
    seats_mapping = {
        VehicleType.COUPE: 2,
        VehicleType.CONVERTIBLE: 2,
        VehicleType.SEDAN: 4,
        VehicleType.HATCHBACK: 4,
        VehicleType.WAGON: 5,
        VehicleType.CROSSOVER: 5,
        VehicleType.SUV: 7,
        VehicleType.MPV: 7,
        VehicleType.VAN: 8,
        VehicleType.PICKUP: 4,
        VehicleType.ELECTRIC: 4,
        VehicleType.LUXURY: 4
    }

    return seats_mapping.get(vehicle_type, 4)  # По умолчанию 4 места