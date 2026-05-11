import random
import string
from db import get_db
from models import Group, GroupMember, User, Subject, Task, UserTask
from datetime import datetime
import os
def generate_group_code(length=6):
    """Генерирует случайный код группы"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def create_group(group_name: str, starosta_id: int):
    db = get_db()
    try:
        while True:
            group_code = generate_group_code()
            existing = db.query(Group).filter(Group.group_code == group_code).first()
            if not existing:
                break
        
        group = Group(
            group_code=group_code,
            group_name=group_name,
            starosta_id=starosta_id
        )
        db.add(group)
        db.commit()
        db.refresh(group)
        
        starosta = db.query(User).filter(User.telegram_id == starosta_id).first()
        if starosta:
            starosta.role = "starosta"
            starosta.group_id = group.id
            db.commit()
            
            member = GroupMember(
                group_id=group.id,
                user_id=starosta.id
            )
            db.add(member)
            db.commit()
        
        print(f"Группа '{group_name}' создана! Код приглашения: {group_code}")
        db.close()
        return group_code
        
    except Exception as e:
        print(f"Ошибка при создании группы: {e}")
        db.rollback()
        db.close()
        return None

def get_group_by_code(group_code: str):
    """возвращает группу по уникальному коду"""
    db = get_db()
    try:
        group = db.query(Group).filter(Group.group_code == group_code).first()
        if group:
            print(f"Группа найдена: {group.group_name}")
        else:
            print(f"Группа с кодом {group_code} не найдена")
        db.close()
        return group
    except Exception as e:
        print(f"Ошибка при поиске группы: {e}")
        db.close()
        return None

def get_group_by_id(group_id: int):
    """возвращает группу по id (хранится в таблицах)"""
    db = get_db()
    try:
        group = db.query(Group).filter(Group.id == group_id).first()
        db.close()
        return group
    except Exception as e:
        print(f"Ошибка при поиске группы: {e}")
        db.close()
        return None

def add_user_to_group(user_id: int, group_id: int):
    """добавляет пользователя в группу по id из баз данных"""
    db = get_db()
    try:
        existing = db.query(GroupMember).filter(
            GroupMember.user_id == user_id,
            GroupMember.group_id == group_id
        ).first()
        
        if existing:
            print(f"Пользователь уже в группе")
            db.close()
            return False
        
        member = GroupMember(
            group_id=group_id,
            user_id=user_id
        )
        db.add(member)
        
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            if user.role == "individual":
                user.role = "group_member"
            user.group_id = group_id
        db.commit()
        print(f"Пользователь добавлен в группу")
        db.close()
        return True
        
    except Exception as e:
        print(f"Ошибка при добавлении в группу: {e}")
        db.rollback()
        db.close()
        return False

def add_user_to_group_by_telegram(telegram_id: int, group_code: str):
    """добавляем пользователя по us в телеграмме и коду группы с использование функции add_user_to_group"""
    db = get_db()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            print(f"Пользователь не найден")
            db.close()
            return False
        
        group = db.query(Group).filter(Group.group_code == group_code).first()
        if not group:
            print(f"Группа с кодом {group_code} не найдена")
            db.close()
            return False
        
        db.close()
        return add_user_to_group(user.id, group.id)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        db.close()
        return False

def get_group_members(group_id: int):
    """возвращает всех пользователей группы по group_id"""
    db = get_db()
    try:
        members = db.query(User).join(GroupMember).filter(GroupMember.group_id == group_id).all()
        print(f"В группе {len(members)} участников")
        db.close()
        return members
    except Exception as e:
        print(f"Ошибка при получении участников: {e}")
        db.close()
        return []

def get_user_groups(user_id: int):
    """возвращает все группы пользователя по id из таблиц"""
    db = get_db()
    try:
        groups = db.query(Group).join(GroupMember).filter(GroupMember.user_id == user_id).all()
        db.close()
        return groups
    except Exception as e:
        print(f"Ошибка: {e}")
        db.close()
        return []

def is_user_in_group(user_id: int, group_id: int):
    """проверяет существует ли пользователь в группе"""
    db = get_db()
    try:
        member = db.query(GroupMember).filter(
            GroupMember.user_id == user_id,
            GroupMember.group_id == group_id
        ).first()
        db.close()
        return member is not None
    except Exception as e:
        print(f"Ошибка: {e}")
        db.close()
        return False

def delete_subject(subject_id: int, user_id=None, group_id=None):
    """Удаляет предмет и все его задания"""
    db = get_db()
    try:
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            print(f"Предмет с id={subject_id} не найден")
            db.close()
            return None

        if group_id is not None and subject.group_id != group_id:
            print(f"Предмет не принадлежит группе {group_id}")
            db.close()
            return None
        if user_id is not None and subject.user_id != user_id:
            print(f"Предмет не принадлежит пользователю {user_id}")
            db.close()
            return None

        deleted_tasks = db.query(Task).filter(
            Task.subject_id == subject_id,
            Task.deadline > datetime.now()
        ).all()
        deleted_count = len(deleted_tasks)

        for task in deleted_tasks:
            db.delete(task)

        db.delete(subject)
        db.commit()

        print(f"Предмет удалён. Удалено будущих заданий: {deleted_count}")
        db.close()
        return deleted_count

    except Exception as e:
        print(f"Ошибка при удалении предмета: {e}")
        db.rollback()
        db.close()
        return None


MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024  
MAX_TASKS_WITH_PHOTO = 200           

def check_storage_limit(group_id=None, user_id=None) -> tuple[bool, str]:
    """Проверяет, не превышен ли лимит хранилища перед сохранением фото"""
    db = get_db()
    try:
        query = db.query(Task).filter(Task.photo_file_id.isnot(None))

        if group_id is not None:
            query = query.filter(Task.group_id == group_id)
        elif user_id is not None:
            query = query.filter(Task.created_by == user_id)

        count = query.count()

        if count >= MAX_TASKS_WITH_PHOTO:
            return False, f"Превышен лимит фото ({MAX_TASKS_WITH_PHOTO} шт.). Удали старые задания с фото."

        return True, ""

    except Exception as e:
        print(f"Ошибка при проверке лимита: {e}")
        return False, "Ошибка при проверке лимита хранилища."
    finally:
        db.close()

def create_task(subject_id: int, title: str, deadline, group_id=None, created_by: int = None, photo_file_id=None):
    """Создаёт задание и привязывает к пользователю"""
    """Создаёт задание. photo_file_id не обязателен, по умолчанию None"""
    if photo_file_id is not None:
        allowed, reason = check_storage_limit(group_id=group_id, user_id=created_by)
        if not allowed:
            print(f"Отказ в сохранении фото: {reason}")
            return None, reason  

    db = get_db()
    try:
        task = Task(
            subject_id=subject_id,
            title=title,
            deadline=deadline,
            group_id=group_id,
            created_by=created_by,
            photo_file_id=photo_file_id
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # привязываем задание к пользователю
        if created_by:
            user = db.query(User).filter(User.id == created_by).first()
            if user:
                user_task = UserTask(
                    task_id=task.id,
                    user_id=user.id,
                    status="active"
                )
                db.add(user_task)
                db.commit()
        
        print(f"Задание '{title}' создано (id={task.id})")
        db.close()
        return task, None 
    except Exception as e:
        print(f"Ошибка при создании задания: {e}")
        db.rollback()
        db.close()
        return None, str(e)
        
        
def get_task_photo(task_id: int):
    """возвращает задание с фото по id задания"""
    db = get_db()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        db.close()
        if task:
            return task.photo_file_id
        return None
    except Exception as e:
        print(f"Ошибка при получении фото задания: {e}")
        db.close()
        return None

def get_user_tasks(user_id: int):
    """возвращает список всех заданий пользователя по его id из таблиц"""
    db = get_db()
    try:
        tasks = db.query(Task).join(UserTask).filter(
            UserTask.user_id == user_id,
            UserTask.status == "active"
        ).all()

        result = [
            {
                "id": task.id,
                "title": task.title,
                "deadline": task.deadline,
                "subject_id": task.subject_id,
                "photo_file_id": task.photo_file_id
            }
            for task in tasks
        ]

        print(f"Заданий у пользователя {user_id}: {len(result)}")
        db.close()
        return result
    except Exception as e:
        print(f"Ошибка при получении заданий: {e}")
        db.close()
        return []

def get_or_create_subject(name: str, group_id=None, user_id=None):
    """возвращает id предмета если он уже есть, если нет создает для конкретного пользователя/группы и возвращает его id"""
    db = get_db()
    try:
        query = db.query(Subject).filter(Subject.name == name)

        if group_id is not None:
            query = query.filter(Subject.group_id == group_id)
        elif user_id is not None:
            query = query.filter(Subject.user_id == user_id)

        subject = query.first()

        if subject:
            print(f"Предмет '{name}' уже существует (id={subject.id})")
            return subject.id

        new_subject = Subject(
            name=name,
            group_id=group_id,
            user_id=user_id
        )
        db.add(new_subject)
        db.commit()
        db.refresh(new_subject)
        print(f"Предмет '{name}' создан (id={new_subject.id})")
        return new_subject.id

    except Exception as e:
        print(f"Ошибка при получении/создании предмета: {e}")
        db.rollback()
        return None
    finally:
        db.close()