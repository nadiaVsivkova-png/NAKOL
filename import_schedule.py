import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from aiogram.filters import Command

download_keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📥 Скачать шаблон")]],
                                        resize_keyboard=True,
                                        one_time_keyboard=True
                                        )

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
                         reply_markup=ReplyKeyboardRemove()
                         )


@dp.message(Command("template"))
async def answer_download(message: Message):
    template_path = "schedule_template.xlsx"

    if os.path.exists(template_path):
        # Отправляем файл
        file = FSInputFile(template_path)
        await message.answer_document(
            document=file,
            caption="📋 Шаблон расписания\n\n"
                    "Заполните файл и отправьте его обратно."
        )
    else:
        await message.answer(
            "❌ Шаблон не найден."
        )


@dp.message(F.text == "📸Отправить фото(распознаю текст)")
async def handle_excel(message: Message):
    await message.answer("Отправь фото расписания. Важно: фото должно быть чётким.",
                         reply_markup=ReplyKeyboardRemove()
                         )


@dp.message(F.text == "✍️Ввести вручную")
async def handle_excel(message: Message):
    await message.answer("Давай добавим занятия по одному.\n\n"
                         "Введи первое занятие в формате:\n"
                         "День, Время начала, Время конца, Предмет\n"
                         "Например: пн, 10:00, 11:30, Математика\n\n"
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
