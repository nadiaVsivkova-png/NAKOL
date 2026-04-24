from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    role = Column(String, nullable=False)  # starosta / group_member / individual
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=True)
    created_at = Column(DateTime, nullable=False)

class Group(Base):
    __tablename__ = 'groups'
    
    id = Column(Integer, primary_key=True)
    group_code = Column(String, unique=True, nullable=False)
    group_name = Column(String, nullable=False)
    starosta_id = Column(Integer, nullable=False)  # telegram_id старосты

class GroupMember(Base):
    __tablename__ = 'group_members'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

class Subject(Base):
    __tablename__ = 'subjects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    title = Column(String, nullable=False)
    deadline = Column(DateTime, nullable=False)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=True)
    created_by = Column(Integer, nullable=False)  # telegram_id

class UserTask(Base):
    __tablename__ = 'user_tasks'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(String, nullable=False)  # active / done
    completed_at = Column(DateTime, nullable=True)

class ReminderSetting(Base):
    __tablename__ = 'reminder_settings'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    mode = Column(String, nullable=False)  # auto / custom / off
    reminder_24h_time = Column(String, nullable=True)  # например "20:00"
    reminder_3h_enabled = Column(Boolean, default=True)

class Meme(Base):
    __tablename__ = 'memes'
    
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)  # photo / text
    content = Column(String, nullable=False)