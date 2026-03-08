import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

BOT_TOKEN = "8798840591:AAG-tpdOTgUkGQKwgXGNvUplOjWQ-Pgh2g0"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Sup! Ты попал NAKOL💫")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())