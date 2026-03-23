from aiogram import Router
from aiogram.types import Message
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'database'))
from user_functions import create_user
from group_functions import create_group

router = Router()

@router.message(lambda m: m.text == "Я староста")
async def starosta_handler(message: Message):
    create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or message.from_user.first_name,
        role="starosta"
    )
    group_code = create_group(
        group_name=f"Группа {message.from_user.first_name}",
        starosta_id=message.from_user.id
    )
    if group_code:
        await message.answer(
            f"🎓 Ты зарегистрирована как староста!\n\n"
            f"Код твоей группы: {group_code}\n\n"
            f"Поделись этим кодом с участниками группы."
        )
    else:
        await message.answer("❌ Ошибка при создании группы. Попробуй снова.")