from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'database'))
from user_functions import get_user

router = Router()

# полный список команд для старосты и индивидуала
FULL_COMMANDS = (
    "/start – начало работы\n"
    "/commands – список всех команд\n"
    "/import_schedule – импорт расписания занятий\n"
    "/import_session – импорт расписания сессии\n"
    "/import_homework – добавить домашнее задание\n"
    "/list – список заданий\n"
    "/done <ID> – отметить задание выполненным\n"
    "/free_time – предложить срочные задания\n"
    "/remind – настройка напоминаний\n"
    "/urgent – срочное уведомление от старосты\n"
    "/remove_subject – удалить предмет\n"
    "/confirm_schedule – подтвердить расписание\n"
    "/edit_schedule – редактировать расписание\n"
    "/template – шаблон расписания\n"
    "/send_to_group – отправить задание группе\n"
    "/session_schedule – посмотреть расписание сессии"
)

# список для участника группы
MEMBER_COMMANDS = (
    "/start – начало работы\n"
    "/commands – список всех команд\n"
    "/list – список заданий\n"
    "/done <ID> – отметить задание выполненным\n"
    "/free_time – предложить срочные задания\n"
    "/remind – настройка напоминаний\n"
    "/session_schedule – посмотреть расписание сессии"
)

@router.message(Command("start"))
async def cmd_start(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Я староста")],
        [KeyboardButton(text="Я в группе")],
        [KeyboardButton(text="Я сам за себя")]
    ], resize_keyboard=True)
    await message.answer("Sup! Ты попал в NAKOL 💫 Кто ты?", reply_markup=kb)

@router.message(Command("commands"))
async def show_commands(message: Message):
    user = get_user(message.from_user.id)
    if user and user.role == "group_member":
        await message.answer(f"📋 Доступные команды:\n\n{MEMBER_COMMANDS}")
    else:
        await message.answer(f"📋 Доступные команды:\n\n{FULL_COMMANDS}")
