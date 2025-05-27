from geopy.distance import geodesic

from core.models import Session, DriverVehicle


def calculate_distance(point1: tuple, point2: tuple) -> float:
    """Расчет расстояния в км между точками (широта, долгота)."""
    return geodesic(point1, point2).km if point1 and point2 else 0.0

async def get_driver_location(driver_id: int) -> tuple:
    """Получение последней локации водителя из БД."""
    with Session() as session:
        driver = session.query(DriverVehicle).filter_by(driver_id=driver_id).first()
        if driver and driver.last_lat and driver.last_lon:
            return (driver.last_lat, driver.last_lon)
    return None