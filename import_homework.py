import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command

Keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📸Отправить фото(распознаю текст) - БЫСТРЫЙ СПОСОБ")],
                                         [KeyboardButton(text="✍️Ввести вручную")]],
                               resize_keyboard=True,
                               one_time_keyboard=True
                               )

bot = Bot(token="Я НЕ ЗНАЮ НАШ ТОКЕН")
dp = Dispatcher()


@dp.message(Command("import_homework"))
async def answer(message: Message):
    await message.answer("Выбери способ загрузки домашнего задания:",
                         reply_markup=Keyboard)


@dp.message(F.text == "📸Отправить фото(распознаю текст) - БЫСТРЫЙ СПОСОБ")
async def handle_excel(message: Message):
    await message.answer("Отправь фото доски, экрана или листка с домашкой.\n"
                         "Важно: фото должно быть чётким.",
                         reply_markup=ReplyKeyboardRemove()
                         )


@dp.message(F.text == "✍️Ввести вручную")
async def handle_excel(message: Message):
    await message.answer("Введи задание в формате:\n"
                         "Предмет, Название, Дедлайн\n"
                         "Например: Математика, №345, 28.03.2026\n\n"
                         "Или отправь /done когда закончишь",
                         reply_markup=ReplyKeyboardRemove()
                         )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
    asyncio.run(main())
