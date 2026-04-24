import asyncio
import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from handlers.start import router as start_router
from handlers.tasks import router as tasks_router
from handlers.registration import router as registration_router
from handlers.join_group import router as join_group_router
from handlers.individual import router as individual_router
from handlers.import_session import router as session_router
from handlers.import_schedule import router as schedule_router
from handlers.import_homework import router as homework_router
from handlers.session_schedule import router as seschedule_router
from handlers.remove_subject import router as remove_router

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(start_router)
dp.include_router(tasks_router)
dp.include_router(registration_router)
dp.include_router(join_group_router)
dp.include_router(individual_router)
dp.include_router(schedule_router)
dp.include_router(homework_router)
dp.include_router(session_router)
dp.include_router(seschedule_router)
dp.include_router(remove_router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
