from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'database'))
from user_functions import get_user, create_user
from group_functions import create_group

router = Router()

STAROSTA_COMMANDS = (
    "📥 <b>Загрузить расписание или домашку</b>\n"
    "/import_schedule – загрузить расписание\n"
    "/import_homework – загрузить домашку\n"
    "/import_session – загрузить расписание сессии\n\n"
    "📋 <b>Мои задания</b>\n"
    "/list – посмотреть список заданий\n"
    "/done – отметить задание выполненным\n"
    "/free_time – предложить срочные задания\n\n"
    "🔔 <b>Уведомления и напоминания</b>\n"
    "/reminder – настроить напоминания\n"
    "/urgent – срочное уведомление от старосты\n\n"
    "⚙️ <b>Управление</b>\n"
    "/schedule – посмотреть расписание\n"
    "/session_schedule – посмотреть расписание сессии\n"
    "/remove_subject – удалить предмет\n\n"
    "📌 <b>Прочее</b>\n"
    "/commands – список всех команд"
)

INDIVIDUAL_COMMANDS = (
    "📥 <b>Загрузить расписание или домашку</b>\n"
    "/import_schedule – загрузить расписание\n"
    "/import_homework – загрузить домашку\n"
    "/import_session – загрузить расписание сессии\n\n"
    "📋 <b>Мои задания</b>\n"
    "/list – посмотреть список заданий\n"
    "/done – отметить задание выполненным\n"
    "/free_time – предложить срочные задания\n\n"
    "🔔 <b>Уведомления и напоминания</b>\n"
    "/reminder – настроить напоминания\n\n"
    "⚙️ <b>Управление</b>\n"
    "/schedule – посмотреть расписание\n"
    "/session_schedule – посмотреть расписание сессии\n"
    "/remove_subject – удалить предмет\n\n"
    "📌 <b>Прочее</b>\n"
    "/commands – список всех команд"
)

MEMBER_COMMANDS = (
    "📋 <b>Мои задания</b>\n"
    "/list – посмотреть список заданий\n"
    "/done – отметить задание выполненным\n"
    "/free_time – предложить срочные задания\n\n"
    "🔔 <b>Уведомления и напоминания</b>\n"
    "/reminder – настроить напоминания\n\n"
    "⚙️ <b>Управление</b>\n"
    "/schedule – посмотреть расписание\n"
    "/session_schedule – посмотреть расписание сессии\n\n"
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
            f"🎉 Ты зарегистрирована как староста!\n\n"
            f"Код твоей группы: {group_code}\n\n"
            f"Поделись этим кодом с участниками группы.",
            reply_markup=ReplyKeyboardRemove()
        )
        await message.answer("Чтобы получить список всех команд, введи /commands")
    else:
        await message.answer("❌ Ошибка при создании группы. Попробуй снова.", reply_markup=ReplyKeyboardRemove())

@router.message(lambda m: m.text == "Я в группе")
async def group_member_handler(message: Message):
    await message.answer("Введи код группы, который прислал староста:", reply_markup=ReplyKeyboardRemove())

@router.message(lambda m: m.text == "Я сам за себя")
async def individual_handler(message: Message):
    create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or message.from_user.first_name,
        role="individual"
    )
    await message.answer("✅ Супер! Ты в индивидуальном режиме", reply_markup=ReplyKeyboardRemove())
    await message.answer("Чтобы получить список всех команд, введи /commands")