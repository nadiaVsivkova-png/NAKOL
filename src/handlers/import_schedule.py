import os
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from aiogram.filters import Command
from parsers.excel_parser import parse_excel_schedule

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


@router.message(F.document)
async def handle_document(message: Message):
    if not message.document.file_name.endswith('.xlsx'):
        await message.answer("❌ Пожалуйста, отправьте файл в формате .xlsx")
        return

    file_info = await message.bot.get_file(message.document.file_id)
    downloaded_file = await message.bot.download_file(file_info.file_path)

    temp_path = f"temp_{message.document.file_name}"
    with open(temp_path, "wb") as f:
        f.write(downloaded_file.getvalue())

    await message.answer("📥 Файл получен. Обрабатываю...")

    lessons = parse_excel_schedule(temp_path)

    if lessons:
        response = "✅ Расписание загружено!\n\n"
        current_day = ""

        for lesson in lessons:
            if lesson['day'] != current_day:
                current_day = lesson['day']
                response += f"\n {current_day.upper()}:\n"
            response += f"   ⏰ {lesson['start_time']}-{lesson['end_time']} - {lesson['subject']}\n"

        await message.answer(response)

    else:
        await message.answer(
            "❌ Не удалось распознать файл.\n\n"
            "Убедитесь, что файл соответствует шаблону:\n"
            "Для расписания: День, Время начала, Время конца, Предмет\n"
            "Для домашки: Предмет, Название, Дедлайн"
        )
