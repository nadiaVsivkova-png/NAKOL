import asyncio
from aiogram import Bot, Dispatcher
from handlers.import_session import router as session_router
from handlers.import_schedule import router as schedule_router
from handlers.import_homework import router as homework_router

bot = Bot(token="Я НЕ ЗНАЮ НАШ ТОКЕН")
dp = Dispatcher()

# Подключаем роутеры
dp.include_router(schedule_router)
dp.include_router(homework_router)
dp.include_router(session_router)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
