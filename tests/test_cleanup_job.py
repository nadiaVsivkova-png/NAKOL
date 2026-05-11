import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'database'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'utils'))

from datetime import datetime, timedelta
from user_functions import create_user, get_user
from group_functions import create_task
from models import Subject, Task, UserTask
from db import get_db
from cleanup_job import delete_old_tasks


def test_delete_old_tasks():
    create_user(telegram_id=800, username="u8", role="individual")
    user = get_user(800)
    db = get_db()
    subject = Subject(name="Математика", user_id=user.id)
    db.add(subject)
    db.commit()
    subject_id = subject.id
    user_id = user.id
    db.close()

    old = create_task(subject_id=subject_id, title="Старое",
                      deadline=datetime.now() - timedelta(days=40), created_by=800)
    fresh = create_task(subject_id=subject_id, title="Свежее",
                        deadline=datetime.now() + timedelta(days=10), created_by=800)
    old_id = old.id
    fresh_id = fresh.id

    db = get_db()
    user_task = UserTask(task_id=old_id, user_id=user_id, status="active")
    db.add(user_task)
    db.commit()
    db.close()

    delete_old_tasks()

    db = get_db()
    assert db.query(Task).filter(Task.id == old_id).first() is None
    assert db.query(UserTask).filter(UserTask.task_id == old_id).first() is None
    assert db.query(Task).filter(Task.id == fresh_id).first() is not None
    db.close()