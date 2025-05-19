import requests
from config import Config
import logging

def format_address(address: str) -> str:
    """Добавляет город по умолчанию, если не указан"""
    if ',' not in address:
        return f"{address}, {Config.DEFAULT_CITY}"
    return address

def calculate_distance(origin: str, destination: str) -> float:
    origin = format_address(origin)
    destination = format_address(destination)
    """Возвращает расстояние в км между точками с обработкой ошибок"""
    try:
        url = f"https://maps.googleapis.com/maps/api/distancematrix/json?units=metric&origins={origin}&destinations={destination}&key={Config.GOOGLE_MAPS_API_KEY}"
        response = requests.get(url).json()

        if response['status'] != 'OK':
            error_msg = f"Google API error: {response.get('error_message', 'Unknown error')}"
            logging.error(error_msg)
            raise ValueError(error_msg)

        element = response['rows'][0]['elements'][0]

        if element['status'] != 'OK':
            raise ValueError(f"Route error: {element.get('status', 'Unknown status')}")

        if 'distance' not in element:
            raise ValueError("No distance data in response")

        return element['distance']['value'] / 1000  # Переводим метры в км

    except Exception as e:
        logging.error(f"Distance calculation failed: {str(e)}")
        raise