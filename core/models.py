from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, LargeBinary, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    language = Column(String(2), default='pl')  # pl/en/ru
    created_at = Column(DateTime, default=datetime.now)
    payment_method = Column(String)
    origin = Column(String)
    destination = Column(String)


class DriverVehicle(Base):
    __tablename__ = 'driver_vehicles'
    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, unique=True)
    driver_name = Column(String)
    model = Column(String)
    color = Column(String)
    year = Column(Integer)
    license_plate = Column(String)
    photo = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    order_type = Column(String)
    origin = Column(String)
    destination = Column(String)
    payment_method = Column(String)
    distance = Column(Float)
    products = Column(String)
    driver_id = Column(Integer)
    driver_name = Column(String)
    price = Column(Float)
    is_night = Column(Boolean)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.now)

    # Связь с таблицей водителей (опционально)
    vehicle = relationship("DriverVehicle", foreign_keys=[driver_id],
                           primaryjoin="Order.driver_id == DriverVehicle.driver_id", uselist=False)


# Инициализация БД
engine = create_engine('sqlite:///data/database.db', echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)