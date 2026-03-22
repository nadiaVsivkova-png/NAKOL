import asyncio
import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from handlers.start import router as start_router
from handlers.individual import router as individual_router

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(start_router)
dp.include_router(individual_router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())