import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'database'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'utils'))

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, User, ReminderSetting, NotificationLog, Task, Subject, UserTask
from db import get_db

@pytest.fixture(autouse=True)
def use_test_db(tmp_path, monkeypatch):
    """Подменяем БД на изолированную in-memory для каждого теста."""
    db_file = str(tmp_path / "test.db")
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def mock_get_db():
        return TestSession()

    import db as db_module
    monkeypatch.setattr(db_module, "get_db", mock_get_db)

    import reminder_functions as nf_module
    monkeypatch.setattr(nf_module, "get_db", mock_get_db)

    yield mock_get_db


def _make_user(get_db_fn, telegram_id: int, username: str = "user") -> User:
    """Создаёт пользователя напрямую через сессию."""
    db = get_db_fn()
    user = User(
        telegram_id=telegram_id,
        username=username,
        role="individual",
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _make_task(get_db_fn, deadline: datetime, user_id: int) -> int:
    """Создаёт Subject + Task + UserTask для пользователя и возвращает task.id"""
    db = get_db_fn()
    subj = Subject(name="Математика", user_id=user_id)
    db.add(subj)
    db.commit()
    db.refresh(subj)

    task = Task(
        subject_id=subj.id,
        title="Задание",
        deadline=deadline,
        created_by=1,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id

    ut = UserTask(task_id=task_id, user_id=user_id, status="active")
    db.add(ut)
    db.commit()
    db.close()
    return task_id


class TestGetReminderSettings:
    def test_returns_existing_settings(self, use_test_db):
        from reminder_functions import get_reminder_settings, set_reminder_settings

        user = _make_user(use_test_db, telegram_id=1001)
        set_reminder_settings(user.id, mode="off")

        settings = get_reminder_settings(user.id)
        assert settings is not None
        assert settings.mode == "off"

    def test_creates_default_settings_if_missing(self, use_test_db):
        from reminder_functions import get_reminder_settings

        user = _make_user(use_test_db, telegram_id=1002)
        settings = get_reminder_settings(user.id)

        assert settings is not None
        assert settings.mode == "auto"
        assert settings.reminder_3h_enabled is True

    def test_no_duplicate_created_on_second_call(self, use_test_db):
        from reminder_functions import get_reminder_settings

        user = _make_user(use_test_db, telegram_id=1003)
        get_reminder_settings(user.id)
        get_reminder_settings(user.id)

        db = use_test_db()
        count = db.query(ReminderSetting).filter(
            ReminderSetting.user_id == user.id
        ).count()
        db.close()
        assert count == 1


class TestSetReminderSettings:
    def test_creates_new_settings(self, use_test_db):
        from reminder_functions import set_reminder_settings

        user = _make_user(use_test_db, telegram_id=2001)
        settings = set_reminder_settings(user.id, mode="auto", reminder_3h_enabled=False)

        assert settings is not None
        assert settings.mode == "auto"
        assert settings.reminder_3h_enabled is False

    def test_updates_existing_settings(self, use_test_db):
        from reminder_functions import set_reminder_settings

        user = _make_user(use_test_db, telegram_id=2002)
        set_reminder_settings(user.id, mode="auto")
        updated = set_reminder_settings(user.id, mode="off")

        assert updated.mode == "off"

    def test_saves_custom_times(self, use_test_db):
        from reminder_functions import set_reminder_settings, get_reminder_settings

        user = _make_user(use_test_db, telegram_id=2003)
        set_reminder_settings(user.id, mode="custom", custom_times=["09:00", "18:00"])

        settings = get_reminder_settings(user.id)
        assert settings.custom_times == ["09:00", "18:00"]

    def test_saves_reminder_24h_time(self, use_test_db):
        from reminder_functions import set_reminder_settings, get_reminder_settings

        user = _make_user(use_test_db, telegram_id=2004)
        set_reminder_settings(user.id, mode="auto", reminder_24h_time="20:00")

        settings = get_reminder_settings(user.id)
        assert settings.reminder_24h_time == "20:00"

    def test_invalid_mode_raises(self, use_test_db):
        from reminder_functions import set_reminder_settings

        user = _make_user(use_test_db, telegram_id=2005)
        with pytest.raises(ValueError):
            set_reminder_settings(user.id, mode="unknown")

    def test_partial_update_does_not_reset_other_fields(self, use_test_db):
        from reminder_functions import set_reminder_settings, get_reminder_settings

        user = _make_user(use_test_db, telegram_id=2006)
        set_reminder_settings(user.id, mode="auto", reminder_24h_time="19:00", reminder_3h_enabled=True)

        set_reminder_settings(user.id, mode="auto")

        settings = get_reminder_settings(user.id)
        assert settings.reminder_24h_time == "19:00"


class TestNotificationLog:
    def test_log_creates_record(self, use_test_db):
        from reminder_functions import log_notification

        user = _make_user(use_test_db, telegram_id=3001)
        task = _make_task(use_test_db, deadline=datetime.utcnow() + timedelta(hours=24), user_id=user.id)

        entry = log_notification(user.id, task, type="24h")
        assert entry is not None
        assert entry.user_id == user.id
        assert entry.task_id == task
        assert entry.type == "24h"

    def test_was_not_sent_returns_false(self, use_test_db):
        from reminder_functions import was_notification_sent

        user = _make_user(use_test_db, telegram_id=3002)
        task = _make_task(use_test_db, deadline=datetime.utcnow() + timedelta(hours=24), user_id=user.id)

        assert was_notification_sent(user.id, task, type="24h") is False

    def test_was_sent_returns_true_after_log(self, use_test_db):
        from reminder_functions import log_notification, was_notification_sent

        user = _make_user(use_test_db, telegram_id=3003)
        task = _make_task(use_test_db, deadline=datetime.utcnow() + timedelta(hours=24), user_id=user.id)

        log_notification(user.id, task, type="3h")

        assert was_notification_sent(user.id, task, type="3h") is True

    def test_different_type_not_counted(self, use_test_db):
        from reminder_functions import log_notification, was_notification_sent

        user = _make_user(use_test_db, telegram_id=3004)
        task = _make_task(use_test_db, deadline=datetime.utcnow() + timedelta(hours=24), user_id=user.id)

        log_notification(user.id, task, type="24h")

        assert was_notification_sent(user.id, task, type="3h") is False

    def test_different_task_not_counted(self, use_test_db):
        from reminder_functions import log_notification, was_notification_sent

        user = _make_user(use_test_db, telegram_id=3005)
        task1 = _make_task(use_test_db, deadline=datetime.utcnow() + timedelta(hours=24), user_id=user.id)
        task2 = _make_task(use_test_db, deadline=datetime.utcnow() + timedelta(hours=48), user_id=user.id)

        log_notification(user.id, task1, type="24h")

        assert was_notification_sent(user.id, task2, type="24h") is False

    def test_multiple_logs_allowed(self, use_test_db):
        """Функция не бросает исключение при повторном логировании"""
        from reminder_functions import log_notification

        user = _make_user(use_test_db, telegram_id=3006)
        task = _make_task(use_test_db, deadline=datetime.utcnow() + timedelta(hours=24), user_id=user.id)

        log_notification(user.id, task, type="24h")
        log_notification(user.id, task, type="24h")

        db = use_test_db()
        count = db.query(NotificationLog).filter(
            NotificationLog.user_id == user.id,
            NotificationLog.task_id == task,
        ).count()
        db.close()
        assert count == 2



class TestGetUsersToNotify:
    def test_auto_mode_24h_window(self, use_test_db):
        from reminder_functions import get_users_to_notify, set_reminder_settings

        deadline = datetime.utcnow() + timedelta(hours=24)
        current = datetime.utcnow()

        user = _make_user(use_test_db, telegram_id=4001)
        _make_task(use_test_db, deadline=deadline, user_id=user.id)
        set_reminder_settings(user.id, mode="auto")

        result = get_users_to_notify(deadline, current)

        assert any(r["user_id"] == user.id and r["notif_type"] == "24h" for r in result)

    def test_auto_mode_3h_window(self, use_test_db):
        from reminder_functions import get_users_to_notify, set_reminder_settings

        deadline = datetime.utcnow() + timedelta(hours=3)
        current = datetime.utcnow()

        user = _make_user(use_test_db, telegram_id=4002)
        _make_task(use_test_db, deadline=deadline, user_id=user.id)
        set_reminder_settings(user.id, mode="auto", reminder_3h_enabled=True)

        result = get_users_to_notify(deadline, current)

        assert any(r["user_id"] == user.id and r["notif_type"] == "3h" for r in result)

    def test_auto_mode_3h_disabled(self, use_test_db):
        from reminder_functions import get_users_to_notify, set_reminder_settings

        deadline = datetime.utcnow() + timedelta(hours=3)
        current = datetime.utcnow()

        user = _make_user(use_test_db, telegram_id=4003)
        _make_task(use_test_db, deadline=deadline, user_id=user.id)
        set_reminder_settings(user.id, mode="auto", reminder_3h_enabled=False)

        result = get_users_to_notify(deadline, current)

        assert not any(r["user_id"] == user.id for r in result)

    def test_off_mode_no_notification(self, use_test_db):
        from reminder_functions import get_users_to_notify, set_reminder_settings

        deadline = datetime.utcnow() + timedelta(hours=24)
        current = datetime.utcnow()

        user = _make_user(use_test_db, telegram_id=4004)
        _make_task(use_test_db, deadline=deadline, user_id=user.id)
        set_reminder_settings(user.id, mode="off")

        result = get_users_to_notify(deadline, current)
        assert not any(r["user_id"] == user.id for r in result)

    def test_custom_mode_matching_time(self, use_test_db):
        from reminder_functions import get_users_to_notify, set_reminder_settings

        current = datetime(2026, 6, 1, 10, 0, 0)  
        deadline = current + timedelta(days=2)     

        user = _make_user(use_test_db, telegram_id=4005)
        _make_task(use_test_db, deadline=deadline, user_id=user.id)
        set_reminder_settings(user.id, mode="custom", custom_times=["10:00", "18:00"])

        result = get_users_to_notify(deadline, current)
        assert any(r["user_id"] == user.id and r["notif_type"] == "custom" for r in result)

    def test_custom_mode_non_matching_time(self, use_test_db):
        from reminder_functions import get_users_to_notify, set_reminder_settings

        current = datetime(2026, 6, 1, 15, 0, 0) 
        deadline = current + timedelta(days=2)

        user = _make_user(use_test_db, telegram_id=4006)
        _make_task(use_test_db, deadline=deadline, user_id=user.id)
        set_reminder_settings(user.id, mode="custom", custom_times=["10:00", "18:00"])

        result = get_users_to_notify(deadline, current)
        assert not any(r["user_id"] == user.id for r in result)

    def test_outside_all_windows_no_notification(self, use_test_db):
        from reminder_functions import get_users_to_notify, set_reminder_settings

        deadline = datetime.utcnow() + timedelta(hours=10)
        current = datetime.utcnow()

        user = _make_user(use_test_db, telegram_id=4007)
        _make_task(use_test_db, deadline=deadline, user_id=user.id)
        set_reminder_settings(user.id, mode="auto")

        result = get_users_to_notify(deadline, current)
        assert not any(r["user_id"] == user.id for r in result)

    def test_returns_telegram_id(self, use_test_db):
        from reminder_functions import get_users_to_notify, set_reminder_settings

        deadline = datetime.utcnow() + timedelta(hours=24)
        current = datetime.utcnow()

        user = _make_user(use_test_db, telegram_id=4008)
        _make_task(use_test_db, deadline=deadline, user_id=user.id)
        set_reminder_settings(user.id, mode="auto")

        result = get_users_to_notify(deadline, current)
        match = next((r for r in result if r["user_id"] == user.id), None)
        assert match is not None
        assert match["telegram_id"] == 4008

    def test_no_tasks_returns_empty(self, use_test_db):
        from reminder_functions import get_users_to_notify

        deadline = datetime.utcnow() + timedelta(hours=24)
        current = datetime.utcnow()

        result = get_users_to_notify(deadline, current)
        assert result == []

    def test_multiple_users_correct_results(self, use_test_db):
        from reminder_functions import get_users_to_notify, set_reminder_settings

        deadline = datetime.utcnow() + timedelta(hours=24)
        current = datetime.utcnow()

        user_on = _make_user(use_test_db, telegram_id=4009, username="on")
        user_off = _make_user(use_test_db, telegram_id=4010, username="off")

        _make_task(use_test_db, deadline=deadline, user_id=user_on.id)
        _make_task(use_test_db, deadline=deadline, user_id=user_off.id)

        set_reminder_settings(user_on.id, mode="auto")
        set_reminder_settings(user_off.id, mode="off")

        result = get_users_to_notify(deadline, current)

        user_ids_in_result = [r["user_id"] for r in result]
        assert user_on.id in user_ids_in_result
        assert user_off.id not in user_ids_in_result
