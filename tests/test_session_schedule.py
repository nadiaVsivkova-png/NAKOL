import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'database'))

from datetime import datetime
from user_functions import create_user, get_user
from models import Subject, Group
from db import get_db, create_session_schedule, get_session_schedule, delete_session_schedule


def test_create_schedule_for_group():
    db = get_db()
    group = Group(group_code="GRP101", group_name="Группа 1", starosta_id=1001)
    db.add(group)
    db.commit()
    group_id = group.id
    subject = Subject(name="Химия", group_id=group_id)
    db.add(subject)
    db.commit()
    subject_id = subject.id
    db.close()

    schedule = create_session_schedule(
        group_id=group_id, user_id=None, subject_id=subject_id,
        date=datetime(2026, 6, 10), start_time="09:00",
        end_time="10:30", classroom="305"
    )

    assert schedule.group_id == group_id
    assert schedule.user_id is None
    assert schedule.classroom == "305"


def test_create_schedule_for_individual():
    create_user(telegram_id=1002, username="test_sched", role="individual")
    user = get_user(1002)
    db = get_db()
    subject = Subject(name="Биология", user_id=user.id)
    db.add(subject)
    db.commit()
    subject_id = subject.id
    user_id = user.id
    db.close()

    schedule = create_session_schedule(
        group_id=None, user_id=user_id, subject_id=subject_id,
        date=datetime(2026, 6, 11), start_time="11:00",
        end_time="12:30", classroom="101"
    )

    assert schedule.user_id == user_id
    assert schedule.group_id is None
    assert schedule.classroom == "101"