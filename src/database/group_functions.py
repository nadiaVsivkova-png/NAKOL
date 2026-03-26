import random
import string
from db import get_db
from models import Group, GroupMember, User

def generate_group_code(length=6):
    """
    Генерирует случайный код группы
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def create_group(group_name: str, starosta_id: int):
    db = get_db()
    try:
        # Генерируем уникальный код группы
        while True:
            group_code = generate_group_code()
            # Проверяем, не занят ли код
            existing = db.query(Group).filter(Group.group_code == group_code).first()
            if not existing:
                break
        
        # Создаем группу
        group = Group(
            group_code=group_code,
            group_name=group_name,
            starosta_id=starosta_id
        )
        db.add(group)
        db.commit()
        db.refresh(group)
        
        # Находим старосту и обновляем его роль и группу
        starosta = db.query(User).filter(User.telegram_id == starosta_id).first()
        if starosta:
            starosta.role = "starosta"
            starosta.group_id = group.id
            db.commit()
            
            # Добавляем старосту в участники группы
            member = GroupMember(
                group_id=group.id,
                user_id=starosta.id
            )
            db.add(member)
            db.commit()
        
        print(f" Группа '{group_name}' создана! Код приглашения: {group_code}")
        db.close()
        return group_code
        
    except Exception as e:
        print(f" Ошибка при создании группы: {e}")
        db.rollback()
        db.close()
        return None

def get_group_by_code(group_code: str):
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
    db = get_db()
    try:
        # Проверяем, не состоит ли уже пользователь в группе
        existing = db.query(GroupMember).filter(
            GroupMember.user_id == user_id,
            GroupMember.group_id == group_id
        ).first()
        
        if existing:
            print(f"Пользователь уже в группе")
            db.close()
            return False
        
        # Добавляем пользователя в группу
        member = GroupMember(
            group_id=group_id,
            user_id=user_id
        )
        db.add(member)
        
        # Обновляем роль пользователя и group_id
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            if user.role == "individual":
                user.role = "group_member"
            user.group_id = group_id
        db.commit()
        print(f" Пользователь добавлен в группу")
        db.close()
        return True
        
    except Exception as e:
        print(f" Ошибка при добавлении в группу: {e}")
        db.rollback()
        db.close()
        return False

def add_user_to_group_by_telegram(telegram_id: int, group_code: str):
    db = get_db()
    try:
        # Находим пользователя
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            print(f" Пользователь не найден")
            db.close()
            return False
        
        # Находим группу по коду
        group = db.query(Group).filter(Group.group_code == group_code).first()
        if not group:
            print(f" Группа с кодом {group_code} не найдена")
            db.close()
            return False
        
        db.close()
        # Добавляем пользователя в группу
        return add_user_to_group(user.id, group.id)
        
    except Exception as e:
        print(f" Ошибка: {e}")
        db.close()
        return False

def get_group_members(group_id: int):
    db = get_db()
    try:
        members = db.query(User).join(GroupMember).filter(GroupMember.group_id == group_id).all()
        print(f" В группе {len(members)} участников")
        db.close()
        return members
    except Exception as e:
        print(f" Ошибка при получении участников: {e}")
        db.close()
        return []

def get_user_groups(user_id: int):
    """
    Получает все группы пользователя
    
    Параметры:
        user_id: ID пользователя
    
    Возвращает:
        список групп
    """
    db = get_db()
    try:
        groups = db.query(Group).join(GroupMember).filter(GroupMember.user_id == user_id).all()
        db.close()
        return groups
    except Exception as e:
        print(f" Ошибка: {e}")
        db.close()
        return []

def is_user_in_group(user_id: int, group_id: int):
    
    db = get_db()
    try:
        member = db.query(GroupMember).filter(
            GroupMember.user_id == user_id,
            GroupMember.group_id == group_id
        ).first()
        db.close()
        return member is not None
    except Exception as e:
        print(f" Ошибка: {e}")
        db.close()
        return False

# Тестирование 
if __name__ == "__main__":
    print("=" * 40)
    print("ТЕСТИРОВАНИЕ ФУНКЦИЙ ГРУПП")
    print("=" * 40)

    from user_functions import create_user, get_user, get_all_users

    # 1. СОЗДАНИЕ СТАРОСТЫ 
    print("\n1. СОЗДАНИЕ СТАРОСТЫ...")
    starosta = create_user(
        telegram_id=999888777,
        username="староста_тест",
        role="individual"
    )

    if starosta:
        #СОХРАНЯЕМ ДАННЫЕ 
        starosta_username = starosta.username
        starosta_tg_id = starosta.telegram_id
        starosta_id = starosta.id
        print(f"   Староста создан: {starosta_username} (ID: {starosta_id})")

        #2. СОЗДАНИЕ ГРУППЫ 
        print("\n2. СОЗДАНИЕ ГРУППЫ...")
        group_code = create_group(
            group_name="ТЕСТ-01",
            starosta_id=starosta_tg_id
        )

        if group_code:
            print(f"    Группа создана! Код: {group_code}")

            #3. ПОИСК ГРУППЫ ПО КОДУ 
            group = get_group_by_code(group_code)

            if group:
                # СОХРАНЯЕМ ID ГРУППЫ
                group_id = group.id
                group_name = group.group_name
                print(f"    Группа найдена: {group_name} (ID: {group_id})")

                # --- 4. СОЗДАНИЕ УЧАСТНИКА ---
                print("\n3. СОЗДАНИЕ УЧАСТНИКА...")
                member = create_user(
                    telegram_id=111222333,
                    username="участник_тест",
                    role="individual"
                )

                if member:
                    # СОХРАНЯЕМ ДАННЫЕ УЧАСТНИКА 
                    member_username = member.username
                    member_id = member.id
                    print(f"    Участник создан: {member_username} (ID: {member_id})")

                    # 5. ДОБАВЛЕНИЕ В ГРУППУ 
                    print("\n4. ДОБАВЛЕНИЕ В ГРУППУ...")
                    add_result = add_user_to_group(member_id, group_id)

                    if add_result:
                        print(f"   Пользователь добавлен в группу")

                        # Проверяем, обновилась ли роль 
                        updated_member = get_user(111222333)
                        if updated_member:
                            print(f"      Новая роль: {updated_member.role}")

                        # 6. ПОЛУЧАЕМ ВСЕХ УЧАСТНИКОВ ГРУППЫ 
                        print("\n5. УЧАСТНИКИ ГРУППЫ:")
                        members_list = get_group_members(group_id)
                        for i, m in enumerate(members_list, 1):
                            print(f"   {i}. {m.username} (роль: {m.role})")

                        #  7. ПРОВЕРКА ЧЛЕНСТВА 
                        from group_functions import is_user_in_group
                        in_group = is_user_in_group(member_id, group_id)
                        print(f"\n6. ПРОВЕРКА ЧЛЕНСТВА: {in_group}")

    print("\n" + "=" * 40)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 40)