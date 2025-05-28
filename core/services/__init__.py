# Замените содержимое core/services/__init__.py на это:

"""
Сервисы для бизнес-логики
"""
from .user_service import UserService
from .price_calculator import PriceCalculatorService
from .maps_service import MapsService, Location
from .driver_notification import driver_notification_service

__all__ = [
    'UserService',
    'PriceCalculatorService',
    'MapsService',
    'Location',
    'driver_notification_service'
]