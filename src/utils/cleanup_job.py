import sys
import os
import logging
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))  

from db import get_db  # потом импорты из проекта
from models import Task, UserTask, SessionSchedule, Schedule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def delete_old_tasks():
    """Удаляет задания, дедлайн которых был более 14 дней назад. работает каждый день"""
    db = get_db()
    try:
        month_ago = datetime.now() - timedelta(days=14)

        old_tasks = db.query(Task).filter(Task.deadline < month_ago).all()
        count = len(old_tasks)

        if count == 0:
            logger.info("Старых заданий не найдено.")
            return

        old_task_ids = [task.id for task in old_tasks]

        # Сначала удаляем связанные UserTask
        db.query(UserTask).filter(UserTask.task_id.in_(old_task_ids)).delete(
            synchronize_session=False
        )
        # Потом сами задания
        db.query(Task).filter(Task.id.in_(old_task_ids)).delete(
            synchronize_session=False
        )

        db.commit()
        logger.info(f"Удалено старых заданий: {count}")

    except Exception as e:
        logger.error(f"Ошибка при очистке старых заданий: {e}")
        db.rollback()
    finally:
        db.close()


def delete_old_schedules():
    """Удаляет все записи из Schedule и SessionSchedule. """
    today = datetime.now()

    if not ((today.month == 2 and today.day == 1) or
            (today.month == 7 and today.day == 1)):
        logger.info("Сегодня не день очистки расписания. Пропускаем.")
        return

    db = get_db()
    try:
        schedule_count = db.query(Schedule).count()
        session_count = db.query(SessionSchedule).count()

        db.query(Schedule).delete(synchronize_session=False)
        db.query(SessionSchedule).delete(synchronize_session=False)

        db.commit()
        logger.info(f"Удалено записей Schedule: {schedule_count}, SessionSchedule: {session_count}")

    except Exception as e:
        logger.error(f"Ошибка при очистке расписаний: {e}")
        db.rollback()
    finally:
        db.close()