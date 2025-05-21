import asyncio
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from core.bot_instance import Bots
from core.handlers.driver import order_handlers, vehicle_handlers
from core.handlers.driver import driver_start  # Добавляем новый импорт

async def main():
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(driver_start.router)  # Водительский старт
    dp.include_router(order_handlers.router)
    dp.include_router(vehicle_handlers.router)
    await dp.start_polling(Bots.driver)

if __name__ == "__main__":
    asyncio.run(main())