from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.orm import sessionmaker, declarative_base
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

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    order_type = Column(String)
    distance = Column(Float)
    price = Column(Float)
    is_night = Column(Boolean)
    status = Column(String, default='pending')  # pending/accepted/rejected
    created_at = Column(DateTime, default=datetime.now)

# Инициализация БД
engine = create_engine('sqlite:///data/database.db', echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
