from sqlalchemy.orm import Session
from datetime import datetime
from db import get_db
from models import User, ReminderSetting

def create_user(telegram_id: int, username: str, role: str, group_id=None):
    "создает нового пользователя"
    db = get_db()
    try:
        # Проверяем, есть ли уже такой пользователь
        existing_user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if existing_user:
            print(f"⚠️ Пользователь с telegram_id {telegram_id} уже существует")
            return existing_user
        
        # Создаем пользователя
        user = User(
            telegram_id=telegram_id,
            username=username,
            role=role,
            group_id=group_id,
            created_at=datetime.now()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Создаем настройки напоминаний для нового пользователя
        settings = ReminderSetting(
            user_id=user.id,
            mode="auto",  # по умолчанию авто
            reminder_3h_enabled=True  # напоминания за 3 часа включены
        )
        db.add(settings)
        db.commit()
        
        print(f"Пользователь {username} успешно создан!")
        return user
    except Exception as e:
        print(f"Ошибка при создании пользователя: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def get_user(telegram_id: int):
    """ищет пользователя по ID в телеграмме"""
    db = get_db()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            print(f"Пользователь найден: {user.username}")
        else:
            print(f"Пользователь с telegram_id {telegram_id} не найден")
        return user
    finally:
        db.close()

def get_user_by_id(user_id: int):
    """
    ищет пользователя по ID в базе данных
    """
    db = get_db()
    try:
        return db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()

def update_user_role(telegram_id: int, new_role: str):
    """
    Обновляет роль пользователя
    """
    db = get_db()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            old_role = user.role
            user.role = new_role
            db.commit()
            print(f"Роль пользователя {user.username} изменена: {old_role} -> {new_role}")
            return True
        else:
            print(f"Пользователь с telegram_id {telegram_id} не найден")
            return False
    except Exception as e:
        print(f"Ошибка при обновлении роли: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def get_all_users():
    """
    Получает и возвращает список всех пользователей
    """
    db = get_db()
    try:
        users = db.query(User).all()
        print(f"Всего пользователей: {len(users)}")
        return users
    finally:
        db.close()

def get_users_by_role(role: str):
    """
    задаем роль, возвращаем список пользователей с заданной ролью
    """
    db = get_db()
    try:
        users = db.query(User).filter(User.role == role).all()
        print(f"📊 Пользователей с ролью '{role}': {len(users)}")
        return users
    finally:
        db.close()

def delete_user(telegram_id: int):
    """
    Удаляет пользователя
    """
    db = get_db()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            # Сначала удаляем связанные настройки
            settings = db.query(ReminderSetting).filter(ReminderSetting.user_id == user.id).first()
            if settings:
                db.delete(settings)
            
            db.delete(user)
            db.commit()
            print(f"Пользователь {user.username} удален")
            return True
        else:
            print(f"Пользователь с telegram_id {telegram_id} не найден")
            return False
    except Exception as e:
        print(f"Ошибка при удалении: {e}")
        db.rollback()
        return False
    finally:
        db.close()

# Функция для тестирования 
if __name__ == "__main__":
    print("=" * 40)
    print("ТЕСТИРОВАНИЕ ФУНКЦИЙ ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 40)
    
    # Создаем тестового пользователя
    user = create_user(
        telegram_id=123456789,
        username="тест_пользователь",
        role="individual"
    )
    
    if user:
        # Получаем пользователя
        found_user = get_user(123456789)
        
        # Обновляем роль
        update_user_role(123456789, "group_member")
        
        # Получаем всех пользователей
        all_users = get_all_users()
        
        # Удаляем тестового пользователя (если нужно)
        # delete_user(123456789)
    
    print("\n Тестирование завершено!")
