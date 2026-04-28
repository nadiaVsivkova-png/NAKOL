from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database.db import get_db, close_db
from database.models import User, Subject
from database.db import get_session_schedule
from datetime import datetime

router = Router()


def format_date(date_obj):
    """Форматирует дату в читаемый вид"""
    if date_obj is None:
        return "Дата не указана"
    if isinstance(date_obj, datetime):
        return date_obj.strftime("%d.%m.%Y")
    if hasattr(date_obj, 'strftime'):
        return date_obj.strftime("%d.%m.%Y")
    return str(date_obj)


def extract_session_data(session):
    """
    Универсальная функция для извлечения данных из сессии
    Работает и с объектами, и со словарями
    """
    # Проверяем, объект ли это (имеет атрибуты)
    if hasattr(session, 'date'):
        # Это объект SQLAlchemy
        date_value = session.date
        start_time = getattr(session, 'start_time', '')
        end_time = getattr(session, 'end_time', '')
        classroom = getattr(session, 'classroom', '')

        # Получаем название предмета
        subject_name = "Неизвестно"
        if hasattr(session, 'subject_id') and session.subject_id:
            db = get_db()
            subject = db.query(Subject).filter(Subject.id == session.subject_id).first()
            if subject:
                subject_name = subject.name
            close_db(db)
    else:
        # Это словарь
        date_value = session.get('date')
        start_time = session.get('start_time', '')
        end_time = session.get('end_time', '')
        classroom = session.get('classroom', '')
        subject_name = session.get('subject_name', session.get('subject', "Неизвестно"))

    return {
        'date': date_value,
        'start_time': start_time,
        'end_time': end_time,
        'classroom': classroom,
        'subject_name': subject_name
    }


@router.message(Command("session_schedule"))
async def show_session_schedule(message: Message, state: FSMContext):
    """Показывает расписание сессии для пользователя/группы"""

    await state.clear()

    # Получаем пользователя из БД
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    # Получаем расписание в зависимости от роли пользователя
    if user.role == "starosta" and user.group_id:
        sessions = get_session_schedule(group_id=user.group_id)
        schedule_type = "📚 **Расписание сессии для группы**"
    else:
        sessions = get_session_schedule(user_id=user.id)
        schedule_type = "👤 **Моё расписание сессии**"

    # Проверяем, есть ли расписание
    if not sessions:
        await message.answer(
            f"{schedule_type}\n\n"
            "📭 **Расписание сессии не загружено.**\n\n"
            "Загрузите расписание через команду:\n"
            "/import_session"
        )
        return

    # Формируем ответ
    response = f"{schedule_type}\n\n"
    response += "📋 **Список экзаменов и занятий:**\n\n"

    current_date = None

    for session in sessions:
        # Извлекаем данные универсальным способом
        data = extract_session_data(session)

        date_display = format_date(data['date'])

        # Группировка по датам
        if date_display != current_date:
            current_date = date_display
            response += f"📅 **{date_display}**\n"

        # Формируем строку времени
        time_str = data['start_time']
        if data['end_time']:
            time_str += f" - {data['end_time']}"

        response += f"   ⏰ {time_str}\n"
        response += f"   📚 {data['subject_name']}\n"

        # Добавляем аудиторию, если есть
        if data['classroom'] and data['classroom'] != "не указана":
            response += f"   🏛 Аудитория: {data['classroom']}\n"

        response += "\n"

    await message.answer(response)
