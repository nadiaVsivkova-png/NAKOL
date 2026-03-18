import sys
import os

# Добавляем путь к проекту (чтобы Python нашел наши модули)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.database.db import engine
from src.database.models import Base

def create_tables():
    """
    Создает все таблицы в базе данных
    """
    print("Создание таблиц в базе данных...")
    
    # Создаем все таблицы
    Base.metadata.create_all(bind=engine)
    
    print("Таблицы успешно созданы!")
    print("Файл базы данных: nakol.db")

def drop_tables():
    """
    Удаляет все таблицы из базы данных (ОСТОРОЖНО!)
    """
    print("Удаление всех таблиц...")
    Base.metadata.drop_all(bind=engine)
    print("Таблицы удалены!")

if __name__ == "__main__":
    print("=" * 40)
    print("ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
    print("=" * 40)
    
    # Создаем таблицы
    create_tables()
    
    # Проверяем, какие таблицы создались
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"\n Созданные таблицы ({len(tables)}):")
    for table in tables:
        print(f"   - {table}")
