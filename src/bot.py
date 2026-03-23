import asyncio
import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from handlers.start import router as start_router
<<<<<<< HEAD
from handlers.tasks import router as tasks_router
=======
from handlers.registration import router as registration_router
from handlers.join_group import router as join_group_router
>>>>>>> lera/task-2-5

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(start_router)
<<<<<<< HEAD
dp.include_router(tasks_router)
=======
dp.include_router(registration_router)
dp.include_router(join_group_router)
>>>>>>> lera/task-2-5

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())