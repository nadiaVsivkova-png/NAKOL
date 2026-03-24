import asyncio
from aiogram import Bot, Dispatcher
from routers import schedule, homework

bot = Bot(token="Я НЕ ЗНАЮ НАШ ТОКЕН")
dp = Dispatcher()

# Подключаем роутеры
dp.include_router(schedule.router)
dp.include_router(homework.router)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
