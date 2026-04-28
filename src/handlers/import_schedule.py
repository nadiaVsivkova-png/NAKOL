import os
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from templates.excel_parser import parse_excel_schedule
from templates.photo_parser import ocr_photo, parse_schedule_from_photo
from database.group_functions import get_or_create_subject
from database.db import get_db, close_db
from database.models import User, Subject
from datetime import datetime
from database.db import create_schedule

router = Router()


# ==================== FSM СОСТОЯНИЯ ДЛЯ РУЧНОГО ВВОДА ====================
class ScheduleManualStates(StatesGroup):
    waiting_for_day = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()
    waiting_for_subject = State()
    waiting_for_more = State()


# ==================== КЛАВИАТУРЫ ====================
schedule_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊Загрузить Excel-файл(рекомендую)")],
        [KeyboardButton(text="📸Отправить фото(распознаю текст)")],
        [KeyboardButton(text="✍️Ввести расписание вручную")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


# ==================== КОМАНДА /import_schedule ====================
@router.message(Command("import_schedule"))
async def import_schedule(message: Message):
    await message.answer("Каким способом хочешь импортировать расписание?",
                         reply_markup=schedule_keyboard)


# ==================== EXCEL ====================
@router.message(F.text == "📊Загрузить Excel-файл(рекомендую)")
async def handle_excel(message: Message):
    await message.answer("Ты выбрал Excel-файл. Скачай шаблон и заполни его: /template\n\n"
                         "После заполнения просто загрузи файл сюда.",
                         reply_markup=ReplyKeyboardRemove())


@router.message(Command("template"))
async def answer_download(message: Message):
    template_path = "templates/schedule_template.xlsx"

    if os.path.exists(template_path):
        file = FSInputFile(template_path)
        await message.answer_document(
            document=file,
            caption="📋 Шаблон расписания\n\n"
                    "Заполните файл и отправьте его обратно."
        )
    else:
        await message.answer("❌ Шаблон не найден.")


# ==================== ФОТО (OCR) ====================
@router.message(F.text == "📸Отправить фото(распознаю текст)")
async def handle_photo_schedule(message: Message):
    await message.answer("Отправь фото расписания. Важно: фото должно быть чётким.",
                         reply_markup=ReplyKeyboardRemove())


# ==================== РУЧНОЙ ВВОД ====================
@router.message(F.text == "✍️Ввести расписание вручную")
async def start_manual_input(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(lessons=[])
    await state.set_state(ScheduleManualStates.waiting_for_day)

    await message.answer(
        "📝 **Пошаговый ввод расписания**\n\n"
        "Введи **день недели** в формате:\n"
        "• пн\n• вт\n• ср\n• чт\n• пт\n• сб\n• вс\n\n❌ /cancel - отменить",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(ScheduleManualStates.waiting_for_day)
async def process_day(message: Message, state: FSMContext):
    day = message.text.strip().lower()
    valid_days = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс',
                  'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']

    day_map = {
        'понедельник': 'пн', 'вторник': 'вт', 'среда': 'ср',
        'четверг': 'чт', 'пятница': 'пт', 'суббота': 'сб', 'воскресенье': 'вс'
    }

    if day not in valid_days and day not in day_map:
        await message.answer("❌ Неверный день. Введи: пн, вт, ср, чт, пт, сб, вс")
        return

    if day in day_map:
        day = day_map[day]

    await state.update_data(temp_day=day)
    await state.set_state(ScheduleManualStates.waiting_for_start_time)
    await message.answer(f"✅ День: {day}\n\nТеперь введи **время начала** (например: 09:00):")


@router.message(ScheduleManualStates.waiting_for_start_time)
async def process_start_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    try:
        start_time = datetime.strptime(time_str, "%H:%M").strftime("%H:%M")
    except ValueError:
        await message.answer("❌ Неверный формат. Пример: 09:00")
        return

    await state.update_data(temp_start_time=start_time)
    await state.set_state(ScheduleManualStates.waiting_for_end_time)
    await message.answer(f"✅ Время начала: {start_time}\n\nТеперь введи **время окончания** (например: 10:30):")


@router.message(ScheduleManualStates.waiting_for_end_time)
async def process_end_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    try:
        end_time = datetime.strptime(time_str, "%H:%M").strftime("%H:%M")
    except ValueError:
        await message.answer("❌ Неверный формат. Пример: 10:30")
        return

    await state.update_data(temp_end_time=end_time)
    await state.set_state(ScheduleManualStates.waiting_for_subject)
    await message.answer(f"✅ Время окончания: {end_time}\n\nТеперь введи **название предметa**:")


@router.message(ScheduleManualStates.waiting_for_subject)
async def process_subject(message: Message, state: FSMContext):
    subject_name = message.text.strip()

    if not subject_name or subject_name.startswith('/'):
        await message.answer("❌ Введи корректное название предмета:")
        return

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    if user.role == "starosta" and user.group_id:
        subject_id = get_or_create_subject(subject_name, group_id=user.group_id)
    else:
        subject_id = get_or_create_subject(subject_name, user_id=user.id)

    if subject_id is None:
        await message.answer(f"❌ Не удалось создать предмет «{subject_name}»")
        return

    data = await state.get_data()
    new_lesson = {
        'day': data.get('temp_day'),
        'start_time': data.get('temp_start_time'),
        'end_time': data.get('temp_end_time'),
        'subject_name': subject_name,
        'subject_id': subject_id
    }

    lessons = data.get('lessons', [])
    lessons.append(new_lesson)
    await state.update_data(lessons=lessons, temp_day=None, temp_start_time=None, temp_end_time=None)

    await message.answer(f"✅ **Добавлено занятие №{len(lessons)}:**\n\n"
                         f"   📅 День: {new_lesson['day']}\n"
                         f"   ⏰ Время: {new_lesson['start_time']} - {new_lesson['end_time']}\n"
                         f"   📚 Предмет: {subject_name}")

    await state.set_state(ScheduleManualStates.waiting_for_more)
    await message.answer("❓ **Что дальше?**\n\n"
                         "/edit_schedule - добавить ещё\n"
                         "/ready - сохранить\n"
                         "/cancel - отменить")


@router.message(ScheduleManualStates.waiting_for_more, Command("edit_schedule"))
async def add_more(message: Message, state: FSMContext):
    await state.set_state(ScheduleManualStates.waiting_for_day)
    await message.answer("Введи **день недели** для нового занятия:")


@router.message(ScheduleManualStates.waiting_for_more, Command("ready"))
async def finish_manual(message: Message, state: FSMContext):
    data = await state.get_data()
    lessons = data.get('lessons', [])

    if not lessons:
        await message.answer("❌ Нет занятий для сохранения.")
        await state.clear()
        return

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    saved_count = 0
    for lesson in lessons:
        if user.role == "starosta" and user.group_id:
            group_id = user.group_id
            user_id = None
        else:
            group_id = None
            user_id = user.id

        # СОХРАНЯЕМ В БД
        create_schedule(
            group_id=group_id,
            user_id=user_id,
            subject_id=lesson['subject_id'],
            weekday=lesson['day'],
            start_time=lesson['start_time'],
            end_time=lesson['end_time'],
            classroom=None
        )
        saved_count += 1

    await message.answer(f"✅ **Расписание сохранено!**\n\n📊 Добавлено занятий: {saved_count}")
    await state.clear()


@router.message(ScheduleManualStates.waiting_for_more, Command("cancel"))
async def cancel_manual(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Ручной ввод отменён.")


# ==================== ОБРАБОТЧИК EXCEL ФАЙЛА ====================
@router.message(F.document)
async def handle_document(message: Message):
    if not message.document.file_name.endswith('.xlsx'):
        await message.answer("❌ Отправьте файл .xlsx")
        return

    file_info = await message.bot.get_file(message.document.file_id)
    downloaded_file = await message.bot.download_file(file_info.file_path)

    temp_path = f"temp_{message.document.file_name}"
    with open(temp_path, "wb") as f:
        f.write(downloaded_file.getvalue())

    await message.answer("📥 Файл получен. Обрабатываю...")

    lessons = parse_excel_schedule(temp_path)
    os.remove(temp_path)

    if not lessons:
        await message.answer("❌ Не удалось распознать файл.")
        return

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    saved_count = 0
    for lesson in lessons:
        if user.role == "starosta" and user.group_id:
            subject_id = get_or_create_subject(lesson['subject'], group_id=user.group_id)
            group_id = user.group_id
            user_id = None
        else:
            subject_id = get_or_create_subject(lesson['subject'], user_id=user.id)
            group_id = None
            user_id = user.id

        if subject_id is None:
            continue

        # СОХРАНЯЕМ В БД
        create_schedule(
            group_id=group_id,
            user_id=user_id,
            subject_id=subject_id,
            weekday=lesson['day'],
            start_time=lesson['start_time'],
            end_time=lesson['end_time'],
            classroom=None
        )
        saved_count += 1

    await message.answer(f"✅ **Расписание сохранено!**\n\n📊 Добавлено занятий: {saved_count}")


# ==================== ОБРАБОТЧИК ФОТО ====================
@router.message(F.photo)
async def handle_photo(message: Message):
    await message.answer("📸 Фото получено. Распознаю текст...")

    photo = message.photo[-1]
    file_info = await message.bot.get_file(photo.file_id)

    temp_path = f"temp_photo_{message.message_id}.jpg"
    await message.bot.download_file(file_info.file_path, temp_path)

    try:
        recognized_text = ocr_photo(temp_path)
        if not recognized_text:
            await message.answer("❌ Текст не распознан")
            return

        lessons = parse_schedule_from_photo(recognized_text)
        if not lessons:
            await message.answer("❌ Не удалось распознать расписание")
            return

        db = get_db()
        user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
        close_db(db)

        saved_count = 0
        for lesson in lessons:
            if user.role == "starosta" and user.group_id:
                subject_id = get_or_create_subject(lesson['subject'], group_id=user.group_id)
                group_id = user.group_id
                user_id = None
            else:
                subject_id = get_or_create_subject(lesson['subject'], user_id=user.id)
                group_id = None
                user_id = user.id

            if subject_id is None:
                continue

            # СОХРАНЯЕМ В БД
            create_schedule(
                group_id=group_id,
                user_id=user_id,
                subject_id=subject_id,
                weekday=lesson['day'],
                start_time=lesson['start_time'],
                end_time=lesson['end_time'],
                classroom=None
            )
            saved_count += 1

        await message.answer(f"✅ **Расписание сохранено!**\n\n📊 Добавлено занятий: {saved_count}")

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ==================== ОТМЕНА ====================
@router.message(Command("cancel"))
async def cancel_all(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=ReplyKeyboardRemove())
