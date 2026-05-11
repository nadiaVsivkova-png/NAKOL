from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database.db import get_db, close_db
from database.models import User, Subject, Schedule
from datetime import datetime

router = Router()


def format_weekday(weekday):
    day_map = {
        'пн': 'Понедельник',
        'вт': 'Вторник',
        'ср': 'Среда',
        'чт': 'Четверг',
        'пт': 'Пятница',
        'сб': 'Суббота',
        'вс': 'Воскресенье'
    }
    return day_map.get(weekday, weekday.capitalize())


def get_schedule(group_id=None, user_id=None):
    """Возвращает расписание для группы или пользователя с учётом типа недели."""
    db = get_db()
    try:
        if group_id is not None:
            schedules = db.query(Schedule).filter(
                Schedule.group_id == group_id
            ).all()
        elif user_id is not None:
            schedules = db.query(Schedule).filter(
                Schedule.user_id == user_id
            ).all()
        else:
            return [], [], []

        # Сортируем в Python
        weekday_order = {'пн': 1, 'вт': 2, 'ср': 3, 'чт': 4, 'пт': 5, 'сб': 6, 'вс': 7}
        schedules.sort(key=lambda x: (weekday_order.get(x.weekday, 99), x.start_time))

        # Разделяем на чётную и нечётную неделю
        even_week = []  # только чётная неделя
        odd_week = []  # только нечётная неделя
        both_weeks = []  # каждая неделя

        for schedule in schedules:
            subject = db.query(Subject).filter(Subject.id == schedule.subject_id).first()
            subject_name = subject.name if subject else "Неизвестно"

            lesson_data = {
                'weekday': schedule.weekday,
                'weekday_display': format_weekday(schedule.weekday),
                'start_time': schedule.start_time,
                'end_time': schedule.end_time,
                'subject_name': subject_name,
                'classroom': schedule.classroom or "не указана",
                'week_type': schedule.week_type if hasattr(schedule, 'week_type') else 'both'
            }

            week_type = lesson_data['week_type']
            if week_type == 'both':
                both_weeks.append(lesson_data)
            elif week_type == 'even':
                even_week.append(lesson_data)
            elif week_type == 'odd':
                odd_week.append(lesson_data)

        return both_weeks, even_week, odd_week
    finally:
        close_db(db)


def build_schedule_message(lessons, title):
    """Строит сообщение с расписанием"""
    if not lessons:
        return None

    response = f"{title}\n\n📋 Список занятий:\n\n"
    current_weekday = None

    for lesson in lessons:
        if lesson['weekday_display'] != current_weekday:
            current_weekday = lesson['weekday_display']
            response += f"\n📅 {current_weekday}\n"

        time_str = lesson['start_time']
        if lesson['end_time']:
            time_str += f" - {lesson['end_time']}"

        response += f"   ⏰ {time_str}\n"
        response += f"   📚 {lesson['subject_name']}\n"

        if lesson['classroom'] and lesson['classroom'] != "не указана":
            response += f"   🏛 Аудитория: {lesson['classroom']}\n"

        response += "\n"

    return response


@router.message(Command("schedule"))
async def show_schedule(message: Message, state: FSMContext):
    await state.clear()

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start")
        return

    # Получаем расписание
    if user.role == "starosta" and user.group_id:
        both_weeks, even_week, odd_week = get_schedule(group_id=user.group_id)
        schedule_type = "📚 Расписание для группы"
    else:
        both_weeks, even_week, odd_week = get_schedule(user_id=user.id)
        schedule_type = "👤 Моё расписание"

    # Проверяем, есть ли вообще расписание
    if not both_weeks and not even_week and not odd_week:
        await message.answer(
            f"{schedule_type}\n\n"
            "📭 Расписание не загружено.\n\n"
            "Загрузите расписание через команду:\n"
            "/import_schedule"
        )
        return

    # Формируем сообщение с предметами, которые есть каждую неделю
    if both_weeks:
        both_message = build_schedule_message(both_weeks, f"{schedule_type} (каждая неделя)")
        if both_message:
            await message.answer(both_message)

    # Формируем сообщение для чётной недели
    # Добавляем в чётную неделю предметы, которые есть каждую неделю
    even_week_full = both_weeks + even_week
    even_week_full.sort(key=lambda x: (x['weekday'], x['start_time']))

    if even_week_full:
        even_message = build_schedule_message(even_week_full, f"{schedule_type} (ЧЁТНАЯ неделя)")
        if even_message:
            await message.answer(even_message)

    # Формируем сообщение для нечётной недели
    # Добавляем в нечётную неделю предметы, которые есть каждую неделю
    odd_week_full = both_weeks + odd_week
    odd_week_full.sort(key=lambda x: (x['weekday'], x['start_time']))

    if odd_week_full:
        odd_message = build_schedule_message(odd_week_full, f"{schedule_type} (НЕЧЁТНАЯ неделя)")
        if odd_message:
            await message.answer(odd_message)

        if schedule['classroom'] and schedule['classroom'] != "не указана":
            response += f"   🏛 Аудитория: {schedule['classroom']}\n"

        response += "\n"

    await message.answer(response)
    await message.answer(response)
    # Если нет предметов ни на одной неделе (только общие)
    if not even_week and not odd_week and both_weeks:
        # Уже отправили общее сообщение, ничего не делаем
        pass
