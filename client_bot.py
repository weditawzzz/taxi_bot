import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

load_dotenv()

bot = Bot(token=os.getenv("CLIENT_BOT_TOKEN"))
dp = Dispatcher()

print("Bot started succesfully")


if __name__ == "__main__":
    from core.handlers.client import start, city_ride
    dp.include_router(start.router)
    dp.include_router(city_ride.router)
    dp.run_polling(bot)