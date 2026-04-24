from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command

router = Router()

homework_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📸Отправить фото(распознаю текст) - БЫСТРЫЙ СПОСОБ")],
              [KeyboardButton(text="✍️Введу вручную")]],
    resize_keyboard=True,
    one_time_keyboard=True)


@router.message(Command("import_homework"))
async def import_homework(message: Message):
    await message.answer("Выбери способ загрузки домашнего задания:",
                         reply_markup=homework_keyboard)


@router.message(F.text == "📸Отправить фото(распознаю текст) - БЫСТРЫЙ СПОСОБ")
async def handle_photo_homework(message: Message):
    await message.answer("Отправь фото доски, экрана или листка с домашкой.\n"
                         "Важно: фото должно быть чётким.",
                         reply_markup=ReplyKeyboardRemove())


@router.message(F.text == "✍️Введу вручную")
async def handle_manual_homework(message: Message):
    await message.answer("Введи задание в формате:\n"
                         "Предмет, Название, Дедлайн\n"
                         "Например: Математика, №345, 28.03.2026\n\n"
                         "Или отправь /done когда закончишь",
                         reply_markup=ReplyKeyboardRemove())
