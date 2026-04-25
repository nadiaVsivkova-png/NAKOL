from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("list"))
async def cmd_list(message: Message):
    await message.answer(
        "📋 Твои задания:\n\n"
        "1. Математика — задачи стр.45 (до пятницы)\n"
        "2. История — реферат про Петра I (до среды)\n"
        "3. Английский — упражнения 3,4,5 (до завтра)"
    )