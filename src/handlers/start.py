from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'database'))
from user_functions import get_user

router = Router()

COMMANDS_TEXT = (
    "/remind — настройка напоминаний\n"
    "/list — посмотреть список домашек\n"
    "/done — отменить задание выполненным\n\n"
    "для старосты и индивидуала:\n"
    "/import_schedule — добавить расписание\n"
    "/import_homework — добавить домашку"
)

@router.message(Command("start"))
async def cmd_start(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Я староста")],
        [KeyboardButton(text="Я в группе")],
        [KeyboardButton(text="Я сам за себя")]
    ], resize_keyboard=True)
    await message.answer("Sup! Ты попал NAKOL💫 Кто ты?", reply_markup=kb)

@router.message(Command("commands"))
async def show_commands(message: Message):
    user = get_user(message.from_user.id)
    if user and user.role == "group_member":
        await message.answer(
            "/remind — настройка напоминаний\n"
            "/list — посмотреть список домашек\n"
            "/done — отметить задание выполненным"
        )
    else:
        await message.answer(COMMANDS_TEXT)
