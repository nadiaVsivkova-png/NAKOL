from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'database'))
from user_functions import get_user

router = Router()

STAROSTA_COMMANDS = (
    "📥 <b>Загрузить расписание или домашку</b>\n"
    "/import_schedule – загрузить расписание\n"
    "/import_homework – загрузить домашку\n"
    "/import_session – загрузить расписание сессии\n"
    "/schedule – посмотреть расписание\n\n"
    "📋 <b>Мои задания</b>\n"
    "/list – посмотреть список заданий\n"
    "/done – отметить задание выполненным\n"
    "/free_time – предложить срочные задания\n\n"
    "🔔 <b>Уведомления и напоминания</b>\n"
    "/reminder – настроить напоминания\n"
    "/urgent – срочное уведомление от старосты\n\n"
    "⚙️ <b>Управление</b>\n"
    "/remove_subject – удалить предмет\n"
    "/session_schedule – посмотреть расписание сессии\n\n"
    "📌 <b>Прочее</b>\n"
    "/commands – список всех команд"
)

INDIVIDUAL_COMMANDS = (
    "📥 <b>Загрузить расписание или домашку</b>\n"
    "/import_schedule – загрузить расписание\n"
    "/import_homework – загрузить домашку\n"
    "/import_session – загрузить расписание сессии\n"
    "/schedule – посмотреть расписание\n\n"
    "📋 <b>Мои задания</b>\n"
    "/list – посмотреть список заданий\n"
    "/done – отметить задание выполненным\n"
    "/free_time – предложить срочные задания\n\n"
    "🔔 <b>Уведомления и напоминания</b>\n"
    "/reminder – настроить напоминания\n\n"
    "⚙️ <b>Управление</b>\n"
    "/remove_subject – удалить предмет\n"
    "/session_schedule – посмотреть расписание сессии\n\n"
    "📌 <b>Прочее</b>\n"
    "/commands – список всех команд"
)

MEMBER_COMMANDS = (
    "📋 <b>Мои задания</b>\n"
    "/list – посмотреть список заданий\n"
    "/done – отметить задание выполненным\n"
    "/free_time – предложить срочные задания\n\n"
    "📥 <b>Расписание</b>\n"
    "/schedule – посмотреть расписание\n\n"
    "🔔 <b>Уведомления и напоминания</b>\n"
    "/reminder – настроить напоминания\n\n"
    "📌 <b>Прочее</b>\n"
    "/commands – список всех команд"
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
        await message.answer(f"📋 Доступные команды:\n\n{MEMBER_COMMANDS}", parse_mode="HTML")
    elif user and user.role == "individual":
        await message.answer(f"📋 Доступные команды:\n\n{INDIVIDUAL_COMMANDS}", parse_mode="HTML")
    else:
        await message.answer(f"📋 Доступные команды:\n\n{STAROSTA_COMMANDS}", parse_mode="HTML")