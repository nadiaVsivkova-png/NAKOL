import pytest
import sys
import os

# Добавляем пути
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'handlers'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'parsers'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'database'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# Регистрируем плагин для асинхронных тестов
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)  # создаём все таблицы во временной БД
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session          # передаём сессию в тест
    session.close()
    Base.metadata.drop_all(engine)


# ========================================

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from aiogram.types import Message, CallbackQuery, User as TgUser, Chat
from aiogram.fsm.context import FSMContext


@pytest.fixture
def mock_db():
    with patch('database.db.get_db') as mock_get_db, \
            patch('database.db.close_db') as mock_close_db:
        mock_session = MagicMock()
        mock_get_db.return_value = mock_session
        yield mock_session, mock_close_db


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 1
    user.telegram_id = "123456789"
    user.username = "testuser"
    user.role = "student"
    user.group_id = None
    user.created_at = datetime.now()
    return user


@pytest.fixture
def mock_user_in_group():
    user = MagicMock()
    user.id = 1
    user.telegram_id = "123456789"
    user.username = "testuser"
    user.role = "student"
    user.group_id = 1
    user.created_at = datetime.now()
    return user


@pytest.fixture
def mock_starosta():
    user = MagicMock()
    user.id = 2
    user.telegram_id = "987654321"
    user.username = "starosta"
    user.role = "starosta"
    user.group_id = 1
    user.created_at = datetime.now()
    return user


@pytest.fixture
def mock_message():
    message = AsyncMock(spec=Message)
    message.from_user = TgUser(id=123456789, first_name="Test", is_bot=False)
    message.chat = Chat(id=123456789, type="private")
    message.text = ""
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_callback():
    callback = AsyncMock(spec=CallbackQuery)
    callback.from_user = TgUser(id=123456789, first_name="Test", is_bot=False)
    callback.message = AsyncMock()
    callback.answer = AsyncMock()
    callback.data = ""
    return callback


@pytest.fixture
def mock_state():
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock(return_value=None)
    state.set_state = AsyncMock(return_value=None)
    state.clear = AsyncMock(return_value=None)
    state.get_state = AsyncMock(return_value=None)
    return state


def create_test_user(session, telegram_id=123456789, role="student", group_id=None):
    from models import User
    user = User(
        telegram_id=telegram_id,
        username=f"user_{telegram_id}",
        role=role,
        group_id=group_id,
        created_at=datetime.now()
    )
    session.add(user)
    session.commit()
    return user


def create_test_subject(session, name="Математика", group_id=None, user_id=None):
    from models import Subject
    subject = Subject(
        name=name,
        group_id=group_id,
        user_id=user_id
    )
    session.add(subject)
    session.commit()
    return subject


def create_test_task(session, subject_id=1, title="Тестовое задание", deadline=None, group_id=None, created_by=1):
    from models import Task
    if deadline is None:
        deadline = datetime.now() + timedelta(days=2)
    task = Task(
        subject_id=subject_id,
        title=title,
        deadline=deadline,
        group_id=group_id,
        created_by=created_by
    )
    session.add(task)
    session.commit()
    return task
