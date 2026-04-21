import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'database'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)  # создаём все таблицы во временной БД
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session          # передаём сессию в тест
    session.close()
    Base.metadata.drop_all(engine)  # после теста всё удаляется