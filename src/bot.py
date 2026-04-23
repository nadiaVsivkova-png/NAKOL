import asyncio
import logging
logging.basicConfig(level=logging.INFO)
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.cleanup_job import delete_old_tasks, delete_old_schedules
BOT_TOKEN = "8798840591:AAG-tpdOTgUkGQKwgXGNvUplOjWQ-Pgh2g0"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Sup! Ты попал NAKOL💫")

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(delete_old_tasks, trigger="cron", hour=3, minute=0)
    scheduler.add_job(delete_old_schedules, trigger="cron", hour=3, minute=0)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())