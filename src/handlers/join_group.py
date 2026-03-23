from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'database'))
from user_functions import create_user
from group_functions import add_user_to_group_by_telegram

router = Router()

class JoinGroup(StatesGroup):
    waiting_for_code = State()

@router.message(lambda m: m.text == "Я в группе")
async def member_handler(message: Message, state: FSMContext):
    create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or message.from_user.first_name,
        role="individual"
    )
    await state.set_state(JoinGroup.waiting_for_code)
    await message.answer("Введи код группы который дала тебе староста:")

@router.message(JoinGroup.waiting_for_code)
async def process_group_code(message: Message, state: FSMContext):
    code = message.text.strip()
    result = add_user_to_group_by_telegram(
        telegram_id=message.from_user.id,
        group_code=code
    )
    if result:
        await message.answer("✅ Ты вступила в группу! Добро пожаловать 🎉")
    else:
        await message.answer("❌ Группа с таким кодом не найдена. Проверь код и попробуй снова.")
    await state.clear()