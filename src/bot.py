import asyncio
from aiogram import Bot, Dispatcher
from handlers.start import router as start_router

BOT_TOKEN = "8798840591:AAG-tpdOTgUkGQKwgXGNvUplOjWQ-Pgh2g0"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(start_router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())