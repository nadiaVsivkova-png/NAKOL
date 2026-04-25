from aiogram import Router
from aiogram.types import Message

router = Router()

@router.message(lambda m: m.text == "Я сам за себя")
async def individual_mode(message: Message):
    await message.answer(
        "✅ Супер! Ты в индивидуальном режиме"
    )
    await message.answer("Чтобы получить список всех команд, введи /commands")
