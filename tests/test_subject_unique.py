import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'database'))

from user_functions import create_user, get_user
from group_functions import get_or_create_subject
from models import Group
from db import get_db


def test_get_or_create_subject_creates_new_for_user():
    """Создаёт новый предмет если его нет у пользователя"""
    create_user(telegram_id=901, username="u_subj1", role="individual")
    user = get_user(901)

    subject_id = get_or_create_subject(name="Математика", user_id=user.id)
    assert subject_id is not None


def test_get_or_create_subject_returns_existing_for_user():
    """Возвращает существующий предмет если уже есть у пользователя"""
    create_user(telegram_id=902, username="u_subj2", role="individual")
    user = get_user(902)

    id1 = get_or_create_subject(name="Физика", user_id=user.id)
    id2 = get_or_create_subject(name="Физика", user_id=user.id)  

    assert id1 == id2  


def test_get_or_create_subject_creates_new_for_group():
    """Создаёт новый предмет если его нет у группы"""
    db = get_db()
    group = Group(group_code="GRP_S01", group_name="Группа S1", starosta_id=9001)
    db.add(group)
    db.commit()
    group_id = group.id
    db.close()

    subject_id = get_or_create_subject(name="История", group_id=group_id)
    assert subject_id is not None


def test_get_or_create_subject_returns_existing_for_group():
    """Возвращает существующий предмет если уже есть у группы"""
    db = get_db()
    group = Group(group_code="GRP_S02", group_name="Группа S2", starosta_id=9002)
    db.add(group)
    db.commit()
    group_id = group.id
    db.close()

    id1 = get_or_create_subject(name="Химия", group_id=group_id)
    id2 = get_or_create_subject(name="Химия", group_id=group_id)  

    assert id1 == id2 


def test_same_name_different_users_are_different_subjects():
    """Одинаковое название у разных пользователей — разные предметы"""
    create_user(telegram_id=903, username="u_subj3", role="individual")
    create_user(telegram_id=904, username="u_subj4", role="individual")
    user1 = get_user(903)
    user2 = get_user(904)

    id1 = get_or_create_subject(name="Биология", user_id=user1.id)
    id2 = get_or_create_subject(name="Биология", user_id=user2.id)

    assert id1 != id2  


def test_same_name_different_groups_are_different_subjects():
    """Одинаковое название у разных групп — разные предметы"""
    db = get_db()
    group1 = Group(group_code="GRP_S03", group_name="Группа S3", starosta_id=9003)
    group2 = Group(group_code="GRP_S04", group_name="Группа S4", starosta_id=9004)
    db.add_all([group1, group2])
    db.commit()
    group1_id = group1.id
    group2_id = group2.id
    db.close()

    id1 = get_or_create_subject(name="География", group_id=group1_id)
    id2 = get_or_create_subject(name="География", group_id=group2_id)

    assert id1 != id2