import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database.db import get_db, close_db
from database.models import User, Task, Subject, GroupMember
# from database.reminder_functions import was_notification_sent, log_notification, get_reminder_settings, \
from database.reminder_functions import was_notification_sent, log_notification, get_reminder_settings, \
    set_reminder_settings

logger = logging.getLogger(__name__)
router = Router()


# ==================== ФУНКЦИЯ ДЛЯ ОТПРАВКИ УВЕДОМЛЕНИЯ ====================

async def send_reminder_to_user(bot: Bot, user_telegram_id: int, task: Task, subject_name: str, notif_type: str):
    """
    Отправляет напоминание одному пользователю.
    notif_type: '24h', '3h' или 'custom_Xh'
    """
    deadline_str = task.deadline.strftime("%d.%m.%Y %H:%M")
    time_left = task.deadline - datetime.now()

    if notif_type == "24h":
        time_text = "24 часа"
    elif notif_type == "3h":
        hours_left = int(time_left.total_seconds() // 3600)
        if hours_left < 1:
            time_text = "менее часа"
        else:
            time_text = f"{hours_left} часа"
    elif notif_type.startswith("custom_"):
        hours = int(notif_type.replace("custom_", "").replace("h", ""))
        time_text = f"{hours} часов"

    message_text = (
        f"⏰ Напоминание о дедлайне!\n\n"
        f"📚 Предмет: {subject_name}\n"
        f"📝 Задание: {task.title}\n"
        f"📅 Дедлайн: {deadline_str}\n\n"
        f"⚠️ Осталось {time_text}!\n"
        f"Не забудь сделать все вовремя!"
    )

    try:
        if task.photo_file_id:
            await bot.send_photo(
                chat_id=user_telegram_id,
                photo=task.photo_file_id,
                caption=message_text,
                parse_mode=None
            )
        else:
            await bot.send_message(
                chat_id=user_telegram_id,
                text=message_text,
                parse_mode=None
            )
        logger.info(f"Уведомление отправлено пользователю {user_telegram_id} по заданию {task.id} ({notif_type})")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки пользователю {user_telegram_id}: {e}")
        return False


# ==================== ОСНОВНАЯ ФУНКЦИЯ ПРОВЕРКИ ДЕДЛАЙНОВ ====================

async def check_and_send_reminders(bot: Bot):
    logger.info("Проверка дедлайнов...")

    db = get_db()
    now = datetime.now()

    upcoming_tasks = db.query(Task).filter(
        Task.deadline > now,
        Task.deadline <= now + timedelta(hours=73)
    ).all()

    if not upcoming_tasks:
        logger.info("Нет заданий с приближающимся дедлайном")
        close_db(db)
        return

    sent_count = 0
    error_count = 0

    for task in upcoming_tasks:
        subject = db.query(Subject).filter(Subject.id == task.subject_id).first()
        subject_name = subject.name if subject else "Неизвестный предмет"

        user_ids = []

        if task.group_id:
            members = db.query(GroupMember).filter(GroupMember.group_id == task.group_id).all()
            user_ids = [m.user_id for m in members]
        else:
            user_ids = [task.created_by]

        if not user_ids:
            continue

        for user_id in user_ids:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.telegram_id:
                continue

            settings = get_reminder_settings(user_id)
            if not settings:
                continue

            time_left = task.deadline - now
            notification_type = None

            auto_24h_enabled = getattr(settings, 'reminder_24h_enabled', True)
            auto_3h_enabled = getattr(settings, 'reminder_3h_enabled', True)

            if auto_24h_enabled and timedelta(hours=23) <= time_left <= timedelta(hours=25):
                notification_type = "24h"
            elif auto_3h_enabled and timedelta(hours=2, minutes=30) <= time_left <= timedelta(hours=3, minutes=30):
                notification_type = "3h"
            else:
                custom_times = getattr(settings, 'custom_times', []) or []
                for hours in custom_times:
                    if isinstance(hours, int) and timedelta(hours=hours - 1) <= time_left <= timedelta(hours=hours + 1):
                        notification_type = f"custom_{hours}h"
                        break

            if not notification_type:
                continue

            if was_notification_sent(user_id, task.id, notification_type):
                continue

            success = await send_reminder_to_user(bot, user.telegram_id, task, subject_name, notification_type)

            if success:
                log_notification(user_id, task.id, notification_type)
                sent_count += 1
            else:
                error_count += 1

    close_db(db)
    logger.info(f"Проверка завершена. Отправлено: {sent_count}, Ошибок: {error_count}")


# ==================== ПЛАНИРОВЩИК ====================

async def start_reminder_scheduler(bot: Bot):
    logger.info("Планировщик напоминаний запущен (проверка каждые 30 минут)")
    while True:
        try:
            await check_and_send_reminders(bot)
        except Exception as e:
            logger.error(f"Ошибка в планировщике: {e}")
        await asyncio.sleep(1800)


# ==================== КОМАНДА ДЛЯ ПРОСМОТРА НАСТРОЕК ====================

@router.message(Command("reminder_settings"))
async def show_reminder_settings(message: Message):
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    settings = get_reminder_settings(user.id)

    custom_times = getattr(settings, 'custom_times', []) or []
    auto_24h_enabled = getattr(settings, 'reminder_24h_enabled', True)
    auto_3h_enabled = getattr(settings, 'reminder_3h_enabled', True)

    response = "⚙️ Настройки напоминаний\n\n"
    response += "📌 Автоматические уведомления:\n"
    response += f"   • За 24 часа: {'✅' if auto_24h_enabled else '❌'}\n"
    response += f"   • За 3 часа: {'✅' if auto_3h_enabled else '❌'}\n"
    response += "\n👤 Персональные напоминания:\n"

    if custom_times:
        for h in custom_times:
            hours_text = "часов" if h % 10 in [0, 5, 6, 7, 8, 9] or (h % 100 in [11, 12, 13, 14]) else (
                "час" if h == 1 else "часа")
            response += f"   • За {h} {hours_text}\n"
    else:
        response += "   📭 Нет персональных напоминаний\n"

    await message.answer(response, parse_mode=None)


# ==================== УПРАВЛЕНИЕ АВТОМАТИЧЕСКИМИ НАПОМИНАНИЯМИ ====================

@router.message(Command("auto_24h_on"))
async def auto_24h_on(message: Message):
    """Включает автоматическое напоминание за 24 часа"""
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    settings = get_reminder_settings(user.id)
    result = set_reminder_settings(user.id, mode=settings.mode, reminder_24h_enabled=True)
    await message.answer("✅ Напоминание за 24 часа включено" if result else "❌ Ошибка")


@router.message(Command("auto_24h_off"))
async def auto_24h_off(message: Message):
    """Отключает автоматическое напоминание за 24 часа"""
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    settings = get_reminder_settings(user.id)
    result = set_reminder_settings(user.id, mode=settings.mode, reminder_24h_enabled=False)
    await message.answer("❌ Напоминание за 24 часа отключено" if result else "❌ Ошибка")


@router.message(Command("auto_3h_on"))
async def auto_3h_on(message: Message):
    """Включает автоматическое напоминание за 3 часа"""
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    settings = get_reminder_settings(user.id)
    result = set_reminder_settings(user.id, mode=settings.mode, reminder_3h_enabled=True)
    await message.answer("✅ Напоминание за 3 часа включено" if result else "❌ Ошибка")


@router.message(Command("auto_3h_off"))
async def auto_3h_off(message: Message):
    """Отключает автоматическое напоминание за 3 часа"""
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    settings = get_reminder_settings(user.id)
    result = set_reminder_settings(user.id, mode=settings.mode, reminder_3h_enabled=False)
    await message.answer("❌ Напоминание за 3 часа отключено" if result else "❌ Ошибка")


# ==================== УПРАВЛЕНИЕ ПЕРСОНАЛЬНЫМИ НАПОМИНАНИЯМИ ====================

@router.message(Command("add_reminder"))
async def add_personal_reminder(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "❌ Укажите количество часов.\n\n"
            "Пример: /add_reminder 6\n"
            "Доступные значения: 1, 2, 3, 4, 5, 6, 8, 10, 12, 24, 48, 72"
        )
        return

    try:
        hours = int(args[1])
        if hours not in [1, 2, 3, 4, 5, 6, 8, 10, 12, 24, 48, 72]:
            await message.answer("❌ Недопустимое количество часов. Выбери: 1, 2, 3, 4, 5, 6, 8, 10, 12, 24, 48, 72")
            return
    except ValueError:
        await message.answer("❌ Введите число")
        return

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    settings = get_reminder_settings(user.id)
    custom_times = getattr(settings, 'custom_times', []) or []

    if hours in custom_times:
        await message.answer(f"⚠️ Напоминание за {hours} часов уже добавлено")
        return

    custom_times.append(hours)
    custom_times.sort()

    result = set_reminder_settings(user.id, mode=settings.mode, custom_times=custom_times)

    if result:
        hours_text = "часов" if hours % 10 in [0, 5, 6, 7, 8, 9] or (hours % 100 in [11, 12, 13, 14]) else (
            "час" if hours == 1 else "часа")
        await message.answer(f"✅ Добавлено напоминание за {hours} {hours_text} до дедлайна")
        await show_reminder_settings(message)
    else:
        await message.answer("❌ Ошибка при добавлении напоминания")


@router.message(Command("remove_reminder"))
async def remove_personal_reminder(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Укажите количество часов.\n\nПример: /remove_reminder 6")
        return

    try:
        hours = int(args[1])
    except ValueError:
        await message.answer("❌ Введите число")
        return

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    settings = get_reminder_settings(user.id)
    custom_times = getattr(settings, 'custom_times', []) or []

    if hours not in custom_times:
        await message.answer(f"⚠️ Напоминание за {hours} часов не найдено")
        return

    custom_times.remove(hours)
    result = set_reminder_settings(user.id, mode=settings.mode, custom_times=custom_times)

    if result:
        await message.answer(f"✅ Удалено напоминание за {hours} часов")
        await show_reminder_settings(message)
    else:
        await message.answer("❌ Ошибка при удалении напоминания")


@router.message(Command("reminder_list"))
async def list_personal_reminders(message: Message):
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    settings = get_reminder_settings(user.id)
    custom_times = getattr(settings, 'custom_times', []) or []

    if not custom_times:
        await message.answer("📭 У вас нет персональных напоминаний.\n\nДобавьте через /add_reminder")
        return

    response = "⏰ Ваши персональные напоминания:\n\n"
    for h in custom_times:
        hours_text = "часов" if h % 10 in [0, 5, 6, 7, 8, 9] or (h % 100 in [11, 12, 13, 14]) else (
            "час" if h == 1 else "часа")
        response += f"• За {h} {hours_text} до дедлайна\n"

    response += "\nУдалить: /remove_reminder <часы>"
    await message.answer(response, parse_mode=None)


# ==================== ОБЩИЕ КОМАНДЫ ====================

@router.message(Command("reminders_off"))
async def reminders_off(message: Message):
    """Отключает все напоминания (авто и персональные)"""
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    result = set_reminder_settings(user.id, mode="off", reminder_24h_enabled=False, reminder_3h_enabled=False,
                                   custom_times=[])
    await message.answer("✅ Все напоминания отключены" if result else "❌ Ошибка")


@router.message(Command("reminders_on"))
async def reminders_on(message: Message):
    """Включает автоматические напоминания по умолчанию (24ч и 3ч)"""
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    result = set_reminder_settings(user.id, mode="auto", reminder_24h_enabled=True, reminder_3h_enabled=True)
    await message.answer("✅ Включены напоминания по умолчанию (за 24ч и за 3ч)" if result else "❌ Ошибка")


@router.message(Command("reminder"))
async def show_remind_commands(message: Message):
    """Показывает все доступные команды для управления напоминаниями"""
    response = (
        "📌 Доступные команды для напоминаний:\n\n"
        "🔔 Управление персональными напоминаниями:\n"
        "• /add_reminder <часы> — добавить напоминание за N часов до дедлайна\n"
        "• /remove_reminder <часы> — удалить напоминание за N часов\n"
        "• /reminder_list — список ваших персональных напоминаний\n\n"
        "🤖 Автоматические напоминания:\n"
        "• /auto_24h_on — включить напоминание за 24 часа\n"
        "• /auto_24h_off — отключить напоминание за 24 часа\n"
        "• /auto_3h_on — включить напоминание за 3 часа\n"
        "• /auto_3h_off — отключить напоминание за 3 часа\n\n"
        "⚙️ Общие настройки:\n"
        "• /reminder_settings — текущие настройки\n"
        "• /reminders_on — включить автоуведомления (24ч и 3ч)\n"
        "• /reminders_off — отключить все напоминания\n"
        "• /reminder — показать эту справку\n\n"
        "💡 Доступные часы: 1, 2, 3, 4, 5, 6, 8, 10, 12, 24, 48, 72\n\n"
        "📌 Пример: /add_reminder 6 — напомнить за 6 часов до дедлайна"
    )
    await message.answer(response, parse_mode=None)
