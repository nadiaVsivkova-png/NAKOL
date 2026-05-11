from aiogram import Router
from aiogram.types import Message
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'database'))
from user_functions import create_user

router = Router()

@router.message(lambda m: m.text == "Я сам за себя")
async def individual_mode(message: Message):
    create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or message.from_user.first_name,
        role="individual"
    )
    await message.answer("✅ Супер! Ты в индивидуальном режиме")
    await message.answer("Чтобы получить список всех команд, введи /commands")
