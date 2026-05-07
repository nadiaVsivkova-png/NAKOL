import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from handlers.start import router as start_router
from handlers.tasks import router as tasks_router
from handlers.registration import router as registration_router
from handlers.join_group import router as join_group_router
from handlers.individual import router as individual_router
from handlers.import_schedule import router as import_schedule_router
from handlers.import_homework import router as import_homework_router
from handlers.urgent import router as urgent_router
from handlers.import_session import router as import_session_router
from handlers.session_schedule import router as session_schedule_router
from handlers.remove_subject import router as remove_subject_router

# from handlers.reminders import router as reminders_router  # сломано, нет reminder_functions

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

dp.include_router(start_router)
dp.include_router(tasks_router)
dp.include_router(registration_router)
dp.include_router(join_group_router)
dp.include_router(individual_router)
dp.include_router(import_schedule_router)
dp.include_router(import_homework_router)
dp.include_router(urgent_router)
dp.include_router(import_session_router)
dp.include_router(session_schedule_router)
dp.include_router(remove_subject_router)
# dp.include_router(reminders_router)


async def main():
    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот выключен")