import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'database'))

from datetime import datetime, timedelta
from group_functions import create_task, delete_subject
from user_functions import create_user, get_user
from models import Subject, Task
from db import get_db


def test_delete_subject_removes_future_tasks_only():
    create_user(telegram_id=600, username="u6", role="individual")
    user = get_user(600)
    db = get_db()
    subject = Subject(name="Физика", user_id=user.id)
    db.add(subject)
    db.commit()
    subject_id = subject.id
    db.close()

    future = create_task(subject_id=subject_id, title="Будущее",
                         deadline=datetime.now() + timedelta(days=5), created_by=600)
    past = create_task(subject_id=subject_id, title="Прошлое",
                       deadline=datetime.now() - timedelta(days=5), created_by=600)
    future_id = future.id
    past_id = past.id

    deleted_count = delete_subject(subject_id=subject_id, user_id=user.id)

    assert deleted_count == 1

    db = get_db()
    assert db.query(Subject).filter(Subject.id == subject_id).first() is None
    assert db.query(Task).filter(Task.id == future_id).first() is None
    assert db.query(Task).filter(Task.id == past_id).first() is not None
    db.close()


def test_delete_subject_wrong_user():
    create_user(telegram_id=700, username="u7", role="individual")
    user = get_user(700)
    db = get_db()
    subject = Subject(name="История", user_id=user.id)
    db.add(subject)
    db.commit()
    subject_id = subject.id
    db.close()

    result = delete_subject(subject_id=subject_id, user_id=9999)
    assert result is None

    db = get_db()
    assert db.query(Subject).filter(Subject.id == subject_id).first() is not None
    db.close()