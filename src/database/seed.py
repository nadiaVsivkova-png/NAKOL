from datetime import datetime, timedelta
from db import get_db
from models import User, Group, Subject, Task, UserTask, Meme
from user_functions import create_user
from group_functions import create_group, add_user_to_group

def seed_database():
    """Заполняет базу тестовыми данными"""
    print("=" * 50)
    print("ЗАПОЛНЕНИЕ БАЗЫ ТЕСТОВЫМИ ДАННЫМИ")
    print("=" * 50)
    
    db = get_db()
    
    try:
        # 1. СОЗДАЁМ ПОЛЬЗОВАТЕЛЕЙ 
        print("\n1. СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ...")
        
        starosta = create_user(
            telegram_id=111111111,
            username="иван_петров",
            role="individual"
        )
        starosta_id = starosta.id
        starosta_username = starosta.username
        starosta_tg = starosta.telegram_id
        
        member = create_user(
            telegram_id=222222222,
            username="анна_смирнова",
            role="individual"
        )
        member_id = member.id
        member_username = member.username
        
        individual = create_user(
            telegram_id=333333333,
            username="петр_сидоров",
            role="individual"
        )
        individual_id = individual.id
        individual_username = individual.username
        
        print(f"    Создано пользователей: 3")
        print(f"      - {starosta_username} (telegram: {starosta_tg})")
        print(f"      - {member_username}")
        print(f"      - {individual_username}")
        
        # 2. СОЗДАЁМ ГРУППУ 
        print("\n2. СОЗДАНИЕ ГРУППЫ...")
        
        group_code = create_group(
            group_name="ИС-21",
            starosta_id=starosta_tg
        )
        
        group = db.query(Group).filter(Group.group_code == group_code).first()
        group_id = group.id
        group_name = group.group_name
        
        print(f"    Группа '{group_name}' создана")
        print(f"      - Код приглашения: {group_code}")
        print(f"      - ID группы: {group_id}")
        
        if group and member:
            add_user_to_group(member_id, group_id)
            print(f"    {member_username} добавлен в группу")
        
        
        # 3. СОЗДАЁМ ПРЕДМЕТЫ 
        print("\n3. СОЗДАНИЕ ПРЕДМЕТОВ...")
        
        subjects = [
            Subject(name="Математика", group_id=group_id, user_id=None),
            Subject(name="Физика", group_id=group_id, user_id=None),
            Subject(name="Программирование", group_id=group_id, user_id=None),
            Subject(name="Английский язык", group_id=None, user_id=individual_id)
        ]
        
        for s in subjects:
            db.add(s)
        db.commit()
        
        subject_ids = [s.id for s in subjects]
        print(f"    Создано предметов: {len(subjects)}")
        for i, s in enumerate(subjects):
            print(f"      - {s.name} (ID: {subject_ids[i]})")
        
        # 4. СОЗДАЁМ ЗАДАНИЯ (6 шт)
        print("\n4. СОЗДАНИЕ ЗАДАНИЙ...")
        
        now = datetime.now()
        
        tasks_data = [
            {"subject_id": subject_ids[0], "title": "Контрольная работа №1", "deadline": now + timedelta(days=7), "group_id": group_id, "created_by": starosta_tg},
            {"subject_id": subject_ids[0], "title": "Домашнее задание №5", "deadline": now + timedelta(days=3), "group_id": group_id, "created_by": starosta_tg},
            {"subject_id": subject_ids[1], "title": "Лабораторная работа №3", "deadline": now + timedelta(days=5), "group_id": group_id, "created_by": starosta_tg},
            {"subject_id": subject_ids[1], "title": "Домашнее задание по физике", "deadline": now + timedelta(days=2), "group_id": group_id, "created_by": starosta_tg},
            {"subject_id": subject_ids[2], "title": "Курсовой проект", "deadline": now + timedelta(days=14), "group_id": group_id, "created_by": starosta_tg},
            {"subject_id": subject_ids[3], "title": "Эссе по английскому", "deadline": now + timedelta(days=4), "group_id": None, "created_by": individual_id}
        ]
        
        tasks = []
        for task_data in tasks_data:
            task = Task(**task_data)
            db.add(task)
            tasks.append(task)
        db.commit()
        
        task_ids = [t.id for t in tasks]
        print(f"    Создано заданий: {len(tasks)}")
        for i, t in enumerate(tasks):
            print(f"      - {t.title} (ID: {task_ids[i]}, дедлайн: {t.deadline.strftime('%d.%m.%Y')})")
        
        # 5. СОЗДАЁМ ЗАДАНИЯ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ 
        print("\n5. СОЗДАНИЕ ЗАДАНИЙ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ...")
        
        user_tasks_data = [
            {"task_id": task_ids[0], "user_id": member_id, "status": "active"},
            {"task_id": task_ids[1], "user_id": member_id, "status": "active"},
            {"task_id": task_ids[2], "user_id": member_id, "status": "active"},
            {"task_id": task_ids[3], "user_id": member_id, "status": "done", "completed_at": now},
            {"task_id": task_ids[4], "user_id": member_id, "status": "active"},
            {"task_id": task_ids[5], "user_id": individual_id, "status": "active"}
        ]
        
        for ut_data in user_tasks_data:
            user_task = UserTask(**ut_data)
            db.add(user_task)
        db.commit()
        print(f"    Создано записей UserTask: {len(user_tasks_data)}")
        
        # 6. СОЗДАЁМ МЕМЫ
        print("\n6. СОЗДАНИЕ МЕМОВ...")
        
        memes_data = [
            {"type": "text", "content": "Дедлайн горит? А ты гори еще быстрее! "},
            {"type": "text", "content": "Студент - это существо, которое спит с открытыми глазами на парах"},
            {"type": "text", "content": "Лучшее время для выполнения задания — сразу после его получения"}
        ]
        
        for meme_data in memes_data:
            meme = Meme(**meme_data)
            db.add(meme)
        db.commit()
        print(f"    Создано мемов: {len(memes_data)}")
        
        print("\n" + "=" * 50)
        print(" БАЗА ДАННЫХ УСПЕШНО ЗАПОЛНЕНА!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n ОШИБКА: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()