import os
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from aiogram.filters import Command

router = Router()

schedule_keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📊Загрузить Excel-файл(рекомендую)")],
                                                  [KeyboardButton(text="📸Отправить фото(распознаю текст)")],
                                                  [KeyboardButton(text="✍️Ввести вручную")]],
                                        resize_keyboard=True,
                                        one_time_keyboard=True)


@router.message(Command("import_schedule"))
async def import_schedule(message: Message):
    await message.answer("Каким способом хочешь импортировать расписание?",
                         reply_markup=schedule_keyboard)


@router.message(F.text == "📊Загрузить Excel-файл(рекомендую)")
async def handle_excel(message: Message):
    await message.answer("Ты выбрал Excel-файл.Скачай шаблон и заполни его: /template\n\n"
                         "После заполнения просто загрузи файл сюда.",
                         reply_markup=ReplyKeyboardRemove())


@router.message(Command("template"))
async def answer_download(message: Message):
    template_path = "schedule_template.xlsx"

    if os.path.exists(template_path):
        file = FSInputFile(template_path)
        await message.answer_document(
            document=file,
            caption="📋 Шаблон расписания\n\n"
                    "Заполните файл и отправьте его обратно."
        )
    else:
        await message.answer("❌ Шаблон не найден.")


@router.message(F.text == "📸Отправить фото(распознаю текст)")
async def handle_photo_schedule(message: Message):
    await message.answer("Отправь фото расписания. Важно: фото должно быть чётким.",
                         reply_markup=ReplyKeyboardRemove())


@router.message(F.text == "✍️Ввести вручную")
async def handle_manual_schedule(message: Message):
    await message.answer("Давай добавим занятия по одному.\n\n"
                         "Введи первое занятие в формате:\n"
                         "День, Время начала, Время конца, Предмет\n"
                         "Например: пн, 10:00, 11:30, Математика\n\n"
                         "Или отправь /done когда закончишь",
                         reply_markup=ReplyKeyboardRemove())
