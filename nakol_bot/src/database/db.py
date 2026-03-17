import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

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