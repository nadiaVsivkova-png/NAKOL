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
    """Возвращает расписание для группы или пользователя."""
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
            return []

        # Сортируем в Python
        weekday_order = {'пн': 1, 'вт': 2, 'ср': 3, 'чт': 4, 'пт': 5, 'сб': 6, 'вс': 7}
        schedules.sort(key=lambda x: (weekday_order.get(x.weekday, 99), x.start_time))

        result = []
        for schedule in schedules:
            subject = db.query(Subject).filter(Subject.id == schedule.subject_id).first()
            result.append({
                'id': schedule.id,
                'weekday': schedule.weekday,
                'start_time': schedule.start_time,
                'end_time': schedule.end_time,
                'subject_name': subject.name if subject else "Неизвестно",
                'classroom': schedule.classroom or "не указана"
            })
        return result
    finally:
        close_db(db)


@router.message(Command("schedule"))
async def show_schedule(message: Message, state: FSMContext):
    await state.clear()

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start")
        return

    if user.role == "starosta" and user.group_id:
        schedules = get_schedule(group_id=user.group_id)
        schedule_type = "📚 Расписание для группы"
    else:
        schedules = get_schedule(user_id=user.id)
        schedule_type = "👤 Моё расписание"

    if not schedules:
        await message.answer(
            f"{schedule_type}\n\n"
            "📭 Расписание не загружено.\n\n"
            "Загрузите расписание через команду:\n"
            "/import_schedule"
        )
        return

    response = f"{schedule_type}\n\n📋 Список занятий:\n\n"
    current_weekday = None

    for schedule in schedules:
        weekday_display = format_weekday(schedule['weekday'])

        if weekday_display != current_weekday:
            current_weekday = weekday_display
            response += f"\n📅 {weekday_display}\n"

        time_str = schedule['start_time']
        if schedule['end_time']:
            time_str += f" - {schedule['end_time']}"

        response += f"   ⏰ {time_str}\n"
        response += f"   📚 {schedule['subject_name']}\n"

        if schedule['classroom'] and schedule['classroom'] != "не указана":
            response += f"   🏛 Аудитория: {schedule['classroom']}\n"

        response += "\n"

    await message.answer(response)