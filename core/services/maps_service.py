"""
Сервис для работы с картами и геолокацией
"""
import logging
from dataclasses import dataclass
from typing import List, Optional
import math

import aiohttp
from geopy.distance import geodesic

from core.config import config
from core.exceptions import ValidationError, ExternalServiceError, NotFoundError, ServiceError

logger = logging.getLogger(__name__)


@dataclass
class Location:
    """Класс для представления местоположения"""
    latitude: float
    longitude: float
    address: str = ""

    def __post_init__(self):
        """Валидация координат"""
        if not (-90 <= self.latitude <= 90):
            raise ValidationError(f"Invalid latitude: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValidationError(f"Invalid longitude: {self.longitude}")

    def distance_to(self, other: 'Location') -> float:
        """Расстояние до другой точки в километрах"""
        return geodesic(
            (self.latitude, self.longitude),
            (other.latitude, other.longitude)
        ).kilometers

    def __str__(self) -> str:
        return f"Location({self.latitude}, {self.longitude})"


@dataclass
class RouteInfo:
    """Информация о маршруте"""
    distance_km: float
    duration_minutes: int
    polyline: Optional[str] = None
    steps: List[str] = None

    def __post_init__(self):
        if self.steps is None:
            self.steps = []


class MapsService:
    """Сервис для работы с картами и геолокацией"""

    def __init__(self):
        self.api_key = config.maps.api_key
        self.base_url = "https://maps.googleapis.com/maps/api"
        self.timeout = aiohttp.ClientTimeout(total=10)

    async def geocode_address(self, address: str) -> Location:
        """Получить координаты по адресу"""
        try:
            # Если нет API ключа, создаем примерные координаты для Щецина
            if self.api_key == 'test_key':
                return self._create_test_location(address)

            url = f"{self.base_url}/geocode/json"
            params = {
                'address': f"{address}, Szczecin, Poland",  # Добавляем город
                'key': self.api_key,
                'region': 'pl',
                'language': 'pl'
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        raise ExternalServiceError(f"Geocoding API error: {response.status}")

                    data = await response.json()

                    if data['status'] != 'OK' or not data.get('results'):
                        return self._create_test_location(address)

                    result = data['results'][0]
                    location = result['geometry']['location']
                    formatted_address = result['formatted_address']

                    return Location(
                        latitude=location['lat'],
                        longitude=location['lng'],
                        address=formatted_address
                    )

        except aiohttp.ClientError as e:
            logger.error(f"Network error during geocoding: {e}")
            return self._create_test_location(address)
        except Exception as e:
            logger.error(f"Unexpected error during geocoding: {e}")
            return self._create_test_location(address)

    def _create_test_location(self, address: str) -> Location:
        """Создать тестовую локацию для Щецина"""
        # Базовые координаты центра Щецина
        base_lat = 53.4285
        base_lng = 14.5528

        # Добавляем небольшие случайные отклонения для разных адресов
        import hashlib
        hash_obj = hashlib.md5(address.encode())
        hash_int = int(hash_obj.hexdigest()[:8], 16)

        # Отклонение в пределах ~5км от центра
        lat_offset = ((hash_int % 1000) - 500) * 0.00001  # ~0.5км макс
        lng_offset = ((hash_int % 2000) - 1000) * 0.00001  # ~1км макс

        return Location(
            latitude=base_lat + lat_offset,
            longitude=base_lng + lng_offset,
            address=f"Szczecin, {address}"
        )

    async def reverse_geocode(self, latitude: float, longitude: float) -> str:
        """Получить адрес по координатам"""
        try:
            if self.api_key == 'test_key':
                return f"Szczecin, coordinates: {latitude:.4f}, {longitude:.4f}"

            url = f"{self.base_url}/geocode/json"
            params = {
                'latlng': f"{latitude},{longitude}",
                'key': self.api_key,
                'language': 'pl'
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.warning(f"Reverse geocoding API error: {response.status}")
                        return f"Szczecin, Lat: {latitude:.4f}, Lng: {longitude:.4f}"

                    data = await response.json()

                    if data['status'] != 'OK' or not data.get('results'):
                        return f"Szczecin, Lat: {latitude:.4f}, Lng: {longitude:.4f}"

                    return data['results'][0]['formatted_address']

        except Exception as e:
            logger.error(f"Error during reverse geocoding: {e}")
            return f"Szczecin, Lat: {latitude:.4f}, Lng: {longitude:.4f}"

    async def get_route(self, origin: Location, destination: Location) -> RouteInfo:
        """Получить информацию о маршруте"""
        try:
            # Если нет API ключа, используем простой расчет
            if self.api_key == 'test_key':
                return self._calculate_simple_route(origin, destination)

            url = f"{self.base_url}/directions/json"
            params = {
                'origin': f"{origin.latitude},{origin.longitude}",
                'destination': f"{destination.latitude},{destination.longitude}",
                'key': self.api_key,
                'mode': 'driving',
                'language': 'pl',
                'units': 'metric'
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.warning(f"Directions API error: {response.status}")
                        return self._calculate_simple_route(origin, destination)

                    data = await response.json()

                    if data['status'] != 'OK' or not data.get('routes'):
                        return self._calculate_simple_route(origin, destination)

                    route = data['routes'][0]
                    leg = route['legs'][0]

                    distance_km = leg['distance']['value'] / 1000
                    duration_minutes = leg['duration']['value'] / 60

                    steps = [step['html_instructions'] for step in leg['steps']]
                    polyline = route.get('overview_polyline', {}).get('points')

                    return RouteInfo(
                        distance_km=distance_km,
                        duration_minutes=int(duration_minutes),
                        polyline=polyline,
                        steps=steps
                    )

        except Exception as e:
            logger.error(f"Error getting route: {e}")
            return self._calculate_simple_route(origin, destination)

    def _calculate_simple_route(self, origin: Location, destination: Location) -> RouteInfo:
        """Простой расчет маршрута без API"""
        distance = origin.distance_to(destination)

        # Ограничиваем расстояние для городских поездок
        if distance > 30:  # Если больше 30км, вероятно ошибка в координатах
            distance = min(distance, 15)  # Максимум 15км для города

        # Примерная скорость в городе - 25 км/ч (с учетом пробок)
        duration = max(int(distance * 2.4), 5)  # Минимум 5 минут

        return RouteInfo(
            distance_km=round(distance, 1),
            duration_minutes=duration,
            steps=[f"Ехать от {origin.address} до {destination.address}"]
        )