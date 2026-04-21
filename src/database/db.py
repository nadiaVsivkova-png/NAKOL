import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
from models import SessionSchedule
from datetime import datetime

# Получаем абсолютный путь к папке, где находится ЭТОТ файл (db.py)
basedir = os.path.abspath(os.path.dirname(__file__))

# Поднимаемся на один уровень вверх (из database/ в src/) и еще раз вверх (из src/ в корень проекта)
# и формируем полный путь к файлу базы данных nakol.db
db_path = os.path.join(basedir, '..', '..', 'nakol.db')
# Преобразуем путь в формат, понятный SQLite (с тройным слешем)
DATABASE_URL = f"sqlite:///{db_path}"

# Для проверки (можно раскомментировать, чтобы увидеть, куда смотрит код)
# print(f"Подключаюсь к базе по пути: {db_path}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    return db

def close_db(db):
    db.close()


def create_session_schedule(group_id, user_id, subject_id, date, start_time, end_time, classroom):
    """Создаёт запись в расписании сессии."""
    db = get_db()
    try:
        schedule = SessionSchedule(
            group_id=group_id,       # для группы — заполнен, для индивидуала — None
            user_id=user_id,         # для индивидуала — заполнен, для группы — None
            subject_id=subject_id,
            date=date,               # объект datetime
            start_time=start_time,   # строка, например "09:00"
            end_time=end_time,       # строка, например "10:30"
            classroom=classroom
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule
    finally:
        close_db(db)


def get_session_schedule(group_id=None, user_id=None):
    """Возвращает список записей расписания"""
    db = get_db()
    try:
        if group_id is not None:
            return db.query(SessionSchedule).filter(
                SessionSchedule.group_id == group_id
            ).order_by(SessionSchedule.date, SessionSchedule.start_time).all()
        elif user_id is not None:
            return db.query(SessionSchedule).filter(
                SessionSchedule.user_id == user_id
            ).order_by(SessionSchedule.date, SessionSchedule.start_time).all()
        else:
            return []
    finally:
        close_db(db)


def delete_session_schedule(schedule_id):
    """Удаляет запись расписания по id."""
    db = get_db()
    try:
        schedule = db.query(SessionSchedule).filter(
            SessionSchedule.id == schedule_id
        ).first()
        if not schedule:
            return False
        db.delete(schedule)
        db.commit()
        return True
    finally:
        close_db(db)