import asyncio
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from core.bot_instance import Bots
from core.handlers.client import start, city_ride, alcohol

async def main():
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(city_ride.router)
    dp.include_router(alcohol.router)
    await dp.start_polling(Bots.client)

if __name__ == "__main__":
    asyncio.run(main())