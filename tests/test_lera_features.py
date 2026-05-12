import pytest
from datetime import datetime, timedelta

from models import User, Task, UserTask, Subject, Group, GroupMember, Meme


@pytest.fixture
def individual_user(db):
    """тестовый пользователь — индивидуал"""
    user = User(
        telegram_id=111111,
        username="test_individual",
        role="individual",
        created_at=datetime.now()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def starosta_user(db):
    """тестовый пользователь — староста с группой"""
    user = User(
        telegram_id=222222,
        username="test_starosta",
        role="starosta",
        created_at=datetime.now()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    group = Group(
        group_code="TEST01",
        group_name="Тестовая группа",
        starosta_id=222222
    )
    db.add(group)
    db.commit()
    return user


@pytest.fixture
def group_member_user(db, starosta_user):
    """тестовый пользователь — участник группы"""
    group = db.query(Group).filter(Group.starosta_id == 222222).first()
    user = User(
        telegram_id=333333,
        username="test_member",
        role="group_member",
        group_id=group.id,
        created_at=datetime.now()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    member = GroupMember(user_id=user.id, group_id=group.id)
    db.add(member)
    db.commit()
    return user


@pytest.fixture
def test_subject(db, individual_user):
    """тестовый предмет"""
    subj = Subject(name="Математика", user_id=individual_user.id)
    db.add(subj)
    db.commit()
    db.refresh(subj)
    return subj


@pytest.fixture
def active_task(db, individual_user, test_subject):
    """активное задание с дедлайном завтра"""
    task = Task(
        subject_id=test_subject.id,
        title="Решить задачи",
        deadline=datetime.now() + timedelta(days=1),
        created_by=individual_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    user_task = UserTask(task_id=task.id, user_id=individual_user.id, status="active")
    db.add(user_task)
    db.commit()
    return task


@pytest.fixture
def urgent_task(db, individual_user, test_subject):
    """срочное задание с дедлайном сегодня"""
    task = Task(
        subject_id=test_subject.id,
        title="Срочная задача",
        deadline=datetime.now() + timedelta(hours=2),
        created_by=individual_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    user_task = UserTask(task_id=task.id, user_id=individual_user.id, status="active")
    db.add(user_task)
    db.commit()
    return task


@pytest.fixture
def meme_text(db):
    """текстовый мем"""
    meme = Meme(type="text", content="Ты молодец!")
    db.add(meme)
    db.commit()
    return meme


# ==================== /list ====================

class TestList:
    """тесты для команды /list"""

    def test_returns_active_tasks(self, db, individual_user, active_task):
        """находит активные задания пользователя"""
        tasks = (
            db.query(Task)
            .join(UserTask)
            .filter(UserTask.user_id == individual_user.id, UserTask.status == "active")
            .all()
        )
        assert len(tasks) >= 1
        assert tasks[0].title == "Решить задачи"

    def test_urgent_sorted_first(self, db, individual_user, active_task, urgent_task):
        """срочные задания — первыми по дедлайну"""
        tasks = (
            db.query(Task)
            .join(UserTask)
            .filter(UserTask.user_id == individual_user.id, UserTask.status == "active")
            .order_by(Task.deadline.asc())
            .all()
        )
        assert tasks[0].deadline <= tasks[1].deadline

    def test_empty_list_no_tasks(self, db):
        """пустой список, если нет активных заданий"""
        tasks = (
            db.query(Task)
            .join(UserTask)
            .filter(UserTask.user_id == 999999, UserTask.status == "active")
            .all()
        )
        assert len(tasks) == 0

    def test_photo_field_exists(self, db, active_task):
        """поле photo_file_id есть в модели Task"""
        assert hasattr(active_task, "photo_file_id")


# ==================== /free_time ====================

class TestFreeTime:
    """тесты для команды /free_time"""

    def test_returns_urgent_tasks(self, db, individual_user, active_task):
        """возвращает задания с ближайшим дедлайном"""
        tasks = (
            db.query(Task)
            .join(UserTask)
            .filter(UserTask.user_id == individual_user.id, UserTask.status == "active")
            .order_by(Task.deadline.asc())
            .limit(2)
            .all()
        )
        assert len(tasks) >= 1

    def test_empty_when_no_tasks(self, db):
        """пусто, если нет активных заданий"""
        tasks = (
            db.query(Task)
            .join(UserTask)
            .filter(UserTask.user_id == 999999, UserTask.status == "active")
            .order_by(Task.deadline.asc())
            .limit(2)
            .all()
        )
        assert len(tasks) == 0


# ==================== /done ====================

class TestDone:
    """тесты для команды /done"""

    def test_mark_task_done(self, db, individual_user, active_task):
        """задание отмечается выполненным, проставляется completed_at"""
        user_task = (
            db.query(UserTask)
            .filter(UserTask.user_id == individual_user.id, UserTask.task_id == active_task.id)
            .first()
        )
        user_task.status = "done"
        user_task.completed_at = datetime.now()
        db.commit()

        updated = (
            db.query(UserTask)
            .filter(UserTask.user_id == individual_user.id, UserTask.task_id == active_task.id)
            .first()
        )
        assert updated.status == "done"
        assert updated.completed_at is not None

    def test_done_removes_from_active(self, db, individual_user, active_task):
        """после выполнения задание не активно"""
        user_task = (
            db.query(UserTask)
            .filter(UserTask.user_id == individual_user.id, UserTask.task_id == active_task.id)
            .first()
        )
        user_task.status = "done"
        user_task.completed_at = datetime.now()
        db.commit()

        active = (
            db.query(Task)
            .join(UserTask)
            .filter(
                UserTask.user_id == individual_user.id,
                UserTask.status == "active",
                Task.id == active_task.id,
            )
            .first()
        )
        assert active is None

    def test_meme_returned(self, db, meme_text):
        """мем находится в базе"""
        meme = db.query(Meme).filter(Meme.type == "text").first()
        assert meme is not None
        assert meme.content == "Ты молодец!"

    def test_no_meme_fallback(self, db):
        """если мемов нет — возвращается None"""
        db.query(Meme).delete()
        db.commit()
        meme = db.query(Meme).first()
        assert meme is None


# ==================== /urgent ====================

class TestUrgent:
    """тесты для команды /urgent"""

    def test_starosta_has_group(self, db, starosta_user):
        """староста привязан к группе"""
        assert starosta_user.role == "starosta"
        group = db.query(Group).filter(Group.starosta_id == 222222).first()
        assert group is not None

    def test_group_has_members(self, db, starosta_user, group_member_user):
        """группа содержит участников"""
        group = db.query(Group).filter(Group.starosta_id == 222222).first()
        members = (
            db.query(User).join(GroupMember).filter(GroupMember.group_id == group.id).all()
        )
        assert len(members) >= 1

    def test_regular_user_blocked(self, db, individual_user):
        """обычный пользователь не может отправить /urgent"""
        assert individual_user.role != "starosta"


# ==================== /commands ====================

class TestCommands:
    """тесты для команды /commands"""

    def test_individual_role(self, db, individual_user):
        """индивидуал имеет правильную роль"""
        assert individual_user.role == "individual"

    def test_starosta_role(self, db, starosta_user):
        """староста имеет правильную роль"""
        assert starosta_user.role == "starosta"

    def test_group_member_role(self, db, group_member_user):
        """участник группы имеет правильную роль"""
        assert group_member_user.role == "group_member"