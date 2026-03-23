import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command

Keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📊Загрузить Excel-файл(рекомендую)")],
                                         [KeyboardButton(text="📸Отправить фото(распознаю текст)")],
                                         [KeyboardButton(text="✍️Ввести вручную")]],
                               resize_keyboard=True,
                               one_time_keyboard=True
                               )

bot = Bot(token="Я НЕ ЗНАЮ НАШ ТОКЕН")
dp = Dispatcher()


@dp.message(Command("import_schedule"))
async def answer(message: Message):
    await message.answer("Каким способом хочешь импортировать расписание?",
                         reply_markup=Keyboard)


@dp.message(F.text == "📊Загрузить Excel-файл(рекомендую)")
async def handle_excel(message: Message):
    await message.answer("Ты выбрал Excel-файл.Скачай шаблон и заполни его: /template\n\n"
                         "После заполнения просто загрузи файл сюда.",
                         reply_markup=ReplyKeyboardRemove()  # Убираем клавиатуру
                         )


@dp.message(F.text == "📸Отправить фото(распознаю текст)")
async def handle_excel(message: Message):
    await message.answer("Ты выбрал отправить фото. Жду твоего расписания!",
                         reply_markup=ReplyKeyboardRemove()
                         )


@dp.message(F.text == "✍️Ввести вручную")
async def handle_excel(message: Message):
    await message.answer("Ты выбрал ввести вручную. Жду твоего расписания!",
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
