import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database.db import get_db, close_db
from database.models import User, Task, Subject, GroupMember, NotificationLog
from database.reminder_functions import was_notification_sent, log_notification

logger = logging.getLogger(__name__)
router = Router()


# ==================== ФУНКЦИЯ ДЛЯ ОТПРАВКИ УВЕДОМЛЕНИЯ ====================

async def send_reminder_to_user(bot: Bot, user_telegram_id: int, task: Task, subject_name: str, notif_type: str):
    """
    Отправляет напоминание одному пользователю.
    '24h' или '3h'
    """
    # Форматируем дедлайн
    deadline_str = task.deadline.strftime("%d.%m.%Y %H:%M")

    # Определяем время до дедлайна
    time_left = task.deadline - datetime.now()
    if notif_type == "24h":
        time_text = "24 часа"
    else:
        hours_left = int(time_left.total_seconds() // 3600)
        if hours_left < 1:
            time_text = "менее часа"
        else:
            time_text = f"{hours_left} часа"

    # Текст напоминания
    message_text = (
        f"⏰ Напоминание о дедлайне!\n\n"
        f"📚 Предмет: {subject_name}\n"
        f"📝 Задание: {task.title}\n"
        f"📅 Дедлайн: {deadline_str}\n\n"
        f"⚠️ Осталось {time_text}!\n"
        f"Не забудь сдать вовремя!"
    )

    try:
        if task.photo_file_id:
            # Отправляем фото с подписью
            await bot.send_photo(
                chat_id=user_telegram_id,
                photo=task.photo_file_id,
                caption=message_text,
                parse_mode="Markdown"
            )
        else:
            # Отправляем только текст
            await bot.send_message(
                chat_id=user_telegram_id,
                text=message_text,
                parse_mode="Markdown"
            )
        logger.info(f"Уведомление отправлено пользователю {user_telegram_id} по заданию {task.id} ({notif_type})")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки пользователю {user_telegram_id}: {e}")
        return False


# ==================== ОСНОВНАЯ ФУНКЦИЯ ПРОВЕРКИ ДЕДЛАЙНОВ ====================

async def check_and_send_reminders(bot: Bot):
    """
    Проверяет дедлайны и отправляет напоминания.
    Запускается каждые 30 минут.
    """
    logger.info("Проверка дедлайнов...")

    db = get_db()
    now = datetime.now()

    # Задания, у которых дедлайн в ближайшие 25 часов (чтобы не пропустить 24ч)
    upcoming_tasks = db.query(Task).filter(
        Task.deadline > now,
        Task.deadline <= now + timedelta(hours=25)
    ).all()

    if not upcoming_tasks:
        logger.info("Нет заданий с приближающимся дедлайном")
        close_db(db)
        return

    sent_count = 0
    error_count = 0

    for task in upcoming_tasks:
        # Получаем предмет
        subject = db.query(Subject).filter(Subject.id == task.subject_id).first()
        subject_name = subject.name if subject else "Неизвестный предмет"

        # Определяем, кому отправлять уведомление
        user_ids = []

        if task.group_id:
            # Групповое задание — отправляем всем участникам группы
            members = db.query(GroupMember).filter(GroupMember.group_id == task.group_id).all()
            user_ids = [m.user_id for m in members]
        else:
            # Индивидуальное задание — только создателю
            user_ids = [task.created_by]

        if not user_ids:
            continue

        # Для каждого пользователя проверяем и отправляем
        for user_id in user_ids:
            # Проверяем, нужно ли отправлять уведомление (24h или 3h)
            time_left = task.deadline - now

            # Определяем тип уведомления
            notification_type = None
            if timedelta(hours=23) <= time_left <= timedelta(hours=25):
                notification_type = "24h"
            elif timedelta(hours=2, minutes=30) <= time_left <= timedelta(hours=3, minutes=30):
                notification_type = "3h"
            else:
                continue  # не подходит ни под один интервал

            # Проверяем, не отправляли ли уже такое уведомление
            if was_notification_sent(user_id, task.id, notification_type):
                continue

            # Получаем telegram_id пользователя
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.telegram_id:
                continue

            # Отправляем уведомление
            success = await send_reminder_to_user(bot, user.telegram_id, task, subject_name, notification_type)

            if success:
                # Логируем отправку
                log_notification(user_id, task.id, notification_type)
                sent_count += 1
            else:
                error_count += 1

    close_db(db)
    logger.info(f"Проверка завершена. Отправлено: {sent_count}, Ошибок: {error_count}")


# ==================== ПЛАНИРОВЩИК ====================

async def start_reminder_scheduler(bot: Bot):
    """
    Запускает фоновую задачу для регулярной проверки дедлайнов.
    Запускается при старте бота.
    """
    logger.info("Планировщик напоминаний запущен (проверка каждые 30 минут)")
    while True:
        try:
            await check_and_send_reminders(bot)
        except Exception as e:
            logger.error(f"Ошибка в планировщике: {e}")
        await asyncio.sleep(1800)  # 30 минут


# ==================== КОМАНДА ДЛЯ ПРОСМОТРА НАСТРОЕК ====================

@router.message(Command("reminder_settings"))
async def show_reminder_settings(message: Message, state: FSMContext):
    """Показывает текущие настройки напоминаний пользователя"""
    from database.reminder_functions import get_reminder_settings

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    settings = get_reminder_settings(user.id)

    if not settings:
        await message.answer("❌ Не удалось получить настройки")
        return

    mode_text = {
        "auto": "Автоматический (за 24ч и за 3ч)",
        "custom": "Пользовательский",
        "off": "Выключены"
    }.get(settings.mode, settings.mode)

    response = f"⚙️ Настройки напоминаний\n\n"
    response += f"Режим: {mode_text}\n"
    if settings.mode == "auto":
        response += f"⏰ Напоминание за 3 часа: {'Включено' if settings.reminder_3h_enabled else 'Выключено'}\n"
    elif settings.mode == "custom" and settings.custom_times:
        times = ", ".join(settings.custom_times)
        response += f"🕐 Пользовательское время: {times}\n"

    await message.answer(response, parse_mode="Markdown")


# ==================== КОМАНДА ДЛЯ ИЗМЕНЕНИЯ НАСТРОЕК ====================

@router.message(Command("set_reminder_off"))
async def set_reminder_off(message: Message, state: FSMContext):
    """Отключает напоминания"""
    from database.reminder_functions import set_reminder_settings

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    result = set_reminder_settings(user.id, mode="off")
    if result:
        await message.answer("✅ Напоминания отключены!")
    else:
        await message.answer("❌ Ошибка при отключении напоминаний")


@router.message(Command("set_reminder_auto"))
async def set_reminder_auto(message: Message, state: FSMContext):
    """Включает автоматические напоминания (за 24ч и за 3ч)"""
    from database.reminder_functions import set_reminder_settings

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    result = set_reminder_settings(user.id, mode="auto", reminder_3h_enabled=True)
    if result:
        await message.answer("✅ Включены автоматические напоминания (за 24ч и за 3ч до дедлайна)")
    else:
        await message.answer("❌ Ошибка при включении напоминаний")


@router.message(Command("set_reminder_3h_off"))
async def set_reminder_3h_off(message: Message, state: FSMContext):
    """Отключает напоминание за 3 часа (оставляет только за 24ч)"""
    from database.reminder_functions import set_reminder_settings, get_reminder_settings

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    result = set_reminder_settings(user.id, mode="auto", reminder_3h_enabled=False)
    if result:
        await message.answer("✅ Напоминание за 3 часа отключено. Осталось только за 24 часа")
    else:
        await message.answer("❌ Ошибка при изменении настроек")
