"""
Модели базы данных с правильной типизацией
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, Enum as SQLEnum, DECIMAL
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


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
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VehicleType(str, Enum):
    """Типы транспортных средств"""
    SEDAN = "sedan"
    HATCHBACK = "hatchback"
    SUV = "suv"
    VAN = "van"
    LUXURY = "luxury"


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
    """Модель транспортного средства"""
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Информация о транспорте
    make: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str] = mapped_column(String(50), nullable=False)
    license_plate: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)

    vehicle_type: Mapped[VehicleType] = mapped_column(SQLEnum(VehicleType), nullable=False)
    seats: Mapped[int] = mapped_column(Integer, nullable=False, default=4)

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
        return f"<Vehicle(id={self.id}, {self.make} {self.model}, plate={self.license_plate})>"


class Ride(Base):
    """Модель поездки"""
    __tablename__ = "rides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    driver_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    vehicle_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("vehicles.id"), nullable=True)

    # Маршрут
    pickup_address: Mapped[str] = mapped_column(Text, nullable=False)
    pickup_lat: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_lng: Mapped[float] = mapped_column(Float, nullable=False)

    destination_address: Mapped[str] = mapped_column(Text, nullable=False)
    destination_lat: Mapped[float] = mapped_column(Float, nullable=False)
    destination_lng: Mapped[float] = mapped_column(Float, nullable=False)

    # Стоимость и расстояние
    distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estimated_price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    final_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2), nullable=True)

    # Статус и время
    status: Mapped[RideStatus] = mapped_column(SQLEnum(RideStatus), nullable=False, default=RideStatus.PENDING)
    passengers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

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