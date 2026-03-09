from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Я староста")],
        [KeyboardButton(text="Я в группе")],
        [KeyboardButton(text="Я сам за себя")]
    ], resize_keyboard=True)
    await message.answer("Sup! Ты попал NAKOL💫 Кто ты?", reply_markup=kb)

@router.message(lambda m: m.text == "Я староста")
async def role_starosta(message: Message):
    await message.answer("Ты староста! Скоро сможешь создать группу 🎓")

@router.message(lambda m: m.text == "Я в группе")
async def role_member(message: Message):
    await message.answer("Ты участник группы! Введи код группы 🔑")

@router.message(lambda m: m.text == "Я сам за себя")
async def role_individual(message: Message):
    await message.answer("Индивидуальный режим! Работаешь самостоятельно 💪")