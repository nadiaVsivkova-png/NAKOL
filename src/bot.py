import asyncio
import logging

logging.basicConfig(level=logging.INFO)
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.cleanup_job import delete_old_tasks, delete_old_schedules
import os
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
from handlers.schedule import router as viewschedule_router
from handlers.reminders import router as reminders_router
from handlers.reminders import start_reminder_scheduler

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
dp.include_router(viewschedule_router)
dp.include_router(reminders_router)


async def main():
    # Запускаем планировщик напоминаний (каждые 30 минут)
    asyncio.create_task(start_reminder_scheduler(bot))

    # Запускаем APScheduler для очистки БД
    scheduler = AsyncIOScheduler()
    scheduler.add_job(delete_old_tasks, trigger="cron", hour=3, minute=0)
    scheduler.add_job(delete_old_schedules, trigger="cron", hour=3, minute=0)
    scheduler.start()
    logger.info("Планировщик очистки БД запущен (ежедневно в 3:00)")

    try:
        await dp.start_polling(bot)
    finally:
        # Graceful shutdown — останавливаем планировщик при выключении бота
        scheduler.shutdown()
        logger.info("Планировщик очистки БД остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот выключен")
