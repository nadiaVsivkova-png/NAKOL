import json
import logging
from datetime import datetime, timedelta

from db import get_db
from models import (
    ReminderSetting, NotificationLog,
    User, Task, UserTask, GroupMember
)

logger = logging.getLogger(__name__)


def get_reminder_settings(user_id: int) -> ReminderSetting | None:
    """Возвращает настройки напоминаний пользователя по его id из таблиц, если записи ещё нет - создаёт по умолчанию"""
    db = get_db()
    try:
        settings = db.query(ReminderSetting).filter(
            ReminderSetting.user_id == user_id
        ).first()

        if settings is None:
            settings = ReminderSetting(
                user_id=user_id,
                mode="auto",
                reminder_3h_enabled=True,
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
            logger.info(f"Созданы дефолтные настройки напоминаний для user_id={user_id}")

        return settings
    except Exception as e:
        logger.error(f"Ошибка get_reminder_settings(user_id={user_id}): {e}")
        db.rollback()
        return None
    finally:
        db.close()


def set_reminder_settings(user_id: int, mode: str, **kwargs) -> ReminderSetting | None:
    """Обновляет/создает настройки напоминаний. в параметр kwargs есть два стандартных напоминания за 24 часа и за 3 (eminder_24h_time, reminder_3h_enabled) и список времен custom_times"""

    if mode not in ("auto", "custom", "off"):
        raise ValueError(f"Недопустимый mode: '{mode}'. Допустимые: auto, custom, off")

    db = get_db()
    try:
        settings = db.query(ReminderSetting).filter(
            ReminderSetting.user_id == user_id
        ).first()

        if settings is None:
            settings = ReminderSetting(user_id=user_id, mode=mode)
            db.add(settings)
        else:
            settings.mode = mode

        if "reminder_24h_time" in kwargs:
            settings.reminder_24h_time = kwargs["reminder_24h_time"]
        if "reminder_3h_enabled" in kwargs:
            settings.reminder_3h_enabled = bool(kwargs["reminder_3h_enabled"])
        if "custom_times" in kwargs:
            settings.custom_times = kwargs["custom_times"]

        db.commit()
        db.refresh(settings)
        logger.info(f"Настройки напоминаний обновлены: user_id={user_id}, mode={mode}")
        return settings
    except Exception as e:
        logger.error(f"Ошибка set_reminder_settings(user_id={user_id}): {e}")
        db.rollback()
        return None
    finally:
        db.close()


def log_notification(user_id: int, task_id: int, type: str) -> NotificationLog | None:
    """вносит в бд, что уведомление было отправлено"""
    db = get_db()
    try:
        entry = NotificationLog(
            user_id=user_id,
            task_id=task_id,
            type=type,
            sent_at=datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info(f"Уведомление залогировано: user_id={user_id}, task_id={task_id}, type={type}")
        return entry
    except Exception as e:
        logger.error(f"Ошибка log_notification: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def was_notification_sent(user_id: int, task_id: int, type: str) -> bool:
    """Возвращает True, если уведомление было отправлено"""
    db = get_db()
    try:
        exists = db.query(NotificationLog).filter(
            NotificationLog.user_id == user_id,
            NotificationLog.task_id == task_id,
            NotificationLog.type == type,
        ).first()
        return exists is not None
    except Exception as e:
        logger.error(f"Ошибка was_notification_sent: {e}")
        return False
    finally:
        db.close()




def _should_notify(settings: ReminderSetting, task_deadline: datetime,
                   current_time: datetime, notif_type: str) -> bool:
    """Проверяет, нужно ли уведомить пользователя с данными настройками."""
    if settings.mode == "off":
        return False

    delta = task_deadline - current_time  

    if settings.mode == "auto":
        if notif_type == "24h":
            return timedelta(hours=23) <= delta <= timedelta(hours=25)
        if notif_type == "3h":
            return settings.reminder_3h_enabled and \
                   timedelta(hours=2, minutes=30) <= delta <= timedelta(hours=3, minutes=30)

    if settings.mode == "custom":
        if notif_type == "custom":
            return True

    return False


def get_users_to_notify(task_deadline: datetime, current_time: datetime) -> list[dict]:
    """Возвращает список пользователей, которым нужно отправить напоминание о задании"""
    db = get_db()
    try:
        tasks = db.query(Task).filter(Task.deadline == task_deadline).all()
        if not tasks:
            return []

        task_ids = [t.id for t in tasks]
        user_tasks = db.query(UserTask).filter(
            UserTask.task_id.in_(task_ids),
            UserTask.status == "active",
        ).all()

        user_ids = list({ut.user_id for ut in user_tasks})

        if not user_ids:
            return []

        users = db.query(User).filter(User.id.in_(user_ids)).all()
        user_map = {u.id: u for u in users}

        settings_list = db.query(ReminderSetting).filter(
            ReminderSetting.user_id.in_(user_ids)
        ).all()
        settings_map = {s.user_id: s for s in settings_list}

        current_hhmm = current_time.strftime("%H:%M")
        result = []

        for uid in user_ids:
            user = user_map.get(uid)
            if not user:
                continue

            settings = settings_map.get(uid)
            if settings is None:
                settings = ReminderSetting(
                    user_id=uid, mode="auto", reminder_3h_enabled=True
                )

            if settings.mode == "off":
                continue

            notif_type = None

            if settings.mode == "auto":
                delta = task_deadline - current_time
                if timedelta(hours=23) <= delta <= timedelta(hours=25):
                    notif_type = "24h"
                elif settings.reminder_3h_enabled and \
                        timedelta(hours=2, minutes=30) <= delta <= timedelta(hours=3, minutes=30):
                    notif_type = "3h"

            elif settings.mode == "custom":
                custom_times = settings.custom_times or []
                if current_hhmm in custom_times:
                    notif_type = "custom"

            if notif_type:
                result.append({
                    "user_id": uid,
                    "telegram_id": user.telegram_id,
                    "notif_type": notif_type,
                })

        return result

    except Exception as e:
        logger.error(f"Ошибка get_users_to_notify: {e}")
        return []
    finally:
        db.close()
