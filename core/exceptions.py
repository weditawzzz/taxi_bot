"""
Система исключений для обработки ошибок
"""
from typing import Optional, Dict, Any


class TaxiBotException(Exception):
    """Базовое исключение для всех ошибок приложения"""

    def __init__(
            self,
            message: str,
            error_code: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"


class ValidationError(TaxiBotException):
    """Ошибка валидации данных"""
    pass


class NotFoundError(TaxiBotException):
    """Объект не найден"""
    pass


class BusinessLogicError(TaxiBotException):
    """Ошибка бизнес-логики"""
    pass


class ServiceError(TaxiBotException):
    """Общая ошибка сервиса"""
    pass


class ExternalServiceError(TaxiBotException):
    """Ошибка внешнего сервиса"""
    pass


class DatabaseError(TaxiBotException):
    """Ошибка базы данных"""
    pass


# Специфичные для такси ошибки
class RideError(TaxiBotException):
    """Ошибка поездки"""
    pass


class DriverNotAvailableError(RideError):
    """Водитель недоступен"""
    pass


class InvalidLocationError(ValidationError):
    """Некорректное местоположение"""
    pass


class PricingError(BusinessLogicError):
    """Ошибка расчета стоимости"""
    pass