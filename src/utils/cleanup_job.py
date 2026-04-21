import sys
import os
import logging
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))

from db import get_db
from models import Task, UserTask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def delete_old_tasks():
    """Удаляет задания, дедлайн которых был более 30 дней назад."""
    db = get_db()
    try:
        month_ago = datetime.now() - timedelta(days=30)

        # Находим старые задания
        old_tasks = db.query(Task).filter(Task.deadline < month_ago).all()
        count = len(old_tasks)

        if count == 0:
            logger.info("Старых заданий не найдено.")
            db.close()
            return

        # Собираем id старых заданий
        old_task_ids = [task.id for task in old_tasks]

        # Сначала удаляем связанные UserTask (каскад не настроен в моделях)
        db.query(UserTask).filter(UserTask.task_id.in_(old_task_ids)).delete(
            synchronize_session=False
        )

        # Потом удаляем сами Task
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