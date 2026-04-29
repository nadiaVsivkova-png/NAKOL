import os
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from aiogram.filters import Command
from parsers.excel_parser import parse_excel_schedule
#from parsers.photo_parser import ocr_photo, parse_schedule_from_photo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import create_session_schedule, get_db, close_db
from database.models import User, Subject
from datetime import datetime


class SessionImportStates(StatesGroup):
    waiting_for_confirmation = State()


class ManualSessionStates(StatesGroup):
    waiting_for_date = State()  # ожидаем дату
    waiting_for_start_time = State()  # ожидаем время начала
    waiting_for_subject = State()  # ожидаем предмет
    waiting_for_classroom = State()  # ожидаем аудиторию
    waiting_for_more = State()  # спрашиваем "добавить ещё?"


router = Router()

schedule_keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📊Загрузить Excel-файл")],
                                                  [KeyboardButton(text="📸Отправить фото расписания сессии(распознаю текст)")],
                                                  [KeyboardButton(text="✍️Ввести расписание вручную")]],
                                        resize_keyboard=True,
                                        one_time_keyboard=True)


@router.message(Command("import_session"))
async def import_session(message: Message):
    await message.answer("Каким способом хочешь импортировать расписание сессии?",
                         reply_markup=schedule_keyboard)


@router.message(F.text == "📊Загрузить Excel-файл")
async def handle_excel(message: Message):
    await message.answer("Ты выбрал Excel-файл.Скачай шаблон и заполни его: /session\n\n"
                         "После заполнения просто загрузи файл сюда.",
                         reply_markup=ReplyKeyboardRemove())


@router.message(Command("session"))
async def answer_download(message: Message):
    template_path = "templates/session_template.xlsx"

    if os.path.exists(template_path):
        file = FSInputFile(template_path)
        await message.answer_document(
            document=file,
            caption="📋 Шаблон расписания\n\n"
                    "Заполните файл и отправьте его обратно."
        )
    else:
        await message.answer("❌ Шаблон не найден.")


@router.message(F.text == "📸Отправить фото расписания сессии(распознаю текст)")
async def handle_photo_schedule(message: Message):
    await message.answer("Отправь фото расписания. Важно: фото должно быть чётким.",
                         reply_markup=ReplyKeyboardRemove())


@router.message(F.text == "✍️Ввести расписание вручную")
async def start_manual_input(message: Message, state: FSMContext):
    """Начинаем пошаговый ввод расписания"""
    # Инициализируем список сессий в состоянии
    await state.update_data(sessions=[])
    await state.set_state(ManualSessionStates.waiting_for_date)

    await message.answer(
        "📝 **Пошаговый ввод расписания**\n\n"
        "Введи **дату** экзамена в формате:\n"
        "• 25.06.2026\n"
        "• 2026-06-25\n"
        "• 25.06.26\n\n"
        "❌ /cancel - отменить ввод"
    )


@router.message(ManualSessionStates.waiting_for_date)
async def process_date(message: Message, state: FSMContext):
    date_str = message.text.strip()

    # Пробуем распарсить дату в разных форматах
    date_formats = ["%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%Y.%m.%d", "%d/%m/%Y"]
    date_value = None

    for fmt in date_formats:
        try:
            date_value = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue

    if date_value is None:
        await message.answer(
            "❌ Неверный формат даты.\n\n"
            "Попробуй ещё раз:\n"
            "• 25.06.2026\n"
            "• 2026-06-25\n"
            "• 25.06.26\n\n"
            "❌ /cancel - отменить"
        )
        return

    # Сохраняем дату
    await state.update_data(temp_date=date_value)
    await state.set_state(ManualSessionStates.waiting_for_start_time)

    await message.answer(
        f"✅ Дата: {date_value.strftime('%d.%m.%Y')}\n\n"
        "Теперь введи **время начала** (например: 09:00 или 9:00):"
    )


@router.message(ManualSessionStates.waiting_for_start_time)
async def process_start_time(message: Message, state: FSMContext):
    time_str = message.text.strip()

    # Проверяем формат времени
    try:
        # Проверяем, что время в формате HH:MM
        start_time = datetime.strptime(time_str, "%H:%M").strftime("%H:%M")
    except ValueError:
        try:
            start_time = datetime.strptime(time_str, "%H:%M").strftime("%H:%M")
        except ValueError:
            await message.answer(
                "❌ Неверный формат времени.\n\n"
                "Попробуй ещё раз (например: 09:00 или 9:00):\n\n"
                "❌ /cancel - отменить"
            )
            return

    await state.update_data(temp_start_time=start_time)
    await state.set_state(ManualSessionStates.waiting_for_subject)

    await message.answer(
        f"✅ Время начала: {start_time}\n\n"
        "Теперь введи **название предмета**:"
    )


@router.message(ManualSessionStates.waiting_for_subject)
async def process_subject(message: Message, state: FSMContext):
    subject_name = message.text.strip()

    if not subject_name or subject_name.startswith('/'):
        await message.answer("❌ Введи корректное название предмета:")
        return

    await state.update_data(temp_subject_name=subject_name)
    await state.update_data(temp_end_time="")
    await state.set_state(ManualSessionStates.waiting_for_classroom)

    await message.answer(
        f"✅ Предмет: {subject_name}\n\n"
        "Теперь введи **аудиторию** (или отправь /skip):"
    )


@router.message(ManualSessionStates.waiting_for_classroom)
async def process_classroom(message: Message, state: FSMContext):
    if message.text == "/skip":
        classroom = ""
    else:
        classroom = message.text.strip()

    # Получаем все временные данные
    data = await state.get_data()
    temp_date = data.get('temp_date')
    temp_start_time = data.get('temp_start_time')
    temp_end_time = data.get('temp_end_time', "")
    temp_subject_name = data.get('temp_subject_name')

    # Создаём новую сессию
    new_session = {
        'date': temp_date,
        'start_time': temp_start_time,
        'end_time': temp_end_time,
        'subject_name': temp_subject_name,
        'classroom': classroom
    }

    # Добавляем в общий список
    sessions = data.get('sessions', [])
    sessions.append(new_session)
    await state.update_data(sessions=sessions)

    # Показываем предпросмотр добавленной сессии
    response = f"✅ **Добавлено занятие №{len(sessions)}:**\n\n"
    response += f"   📅 Дата: {temp_date.strftime('%d.%m.%Y')}\n"
    response += f"   ⏰ Время: {temp_start_time}"
    if temp_end_time:
        response += f" - {temp_end_time}"
    response += f"\n   📚 Предмет: {temp_subject_name}\n"
    if classroom:
        response += f"   🏛 Аудитория: {classroom}\n"

    await message.answer(response)

    await state.set_state(ManualSessionStates.waiting_for_more)

    await message.answer(
        "❓ **Что дальше?**\n\n"
        "✅ /add - добавить ещё одно занятие\n"
        "✅ /ready - завершить и показать предпросмотр\n"
        "❌ /cancel - отменить всё"
    )


@router.message(ManualSessionStates.waiting_for_more, Command("add"))
async def add_more(message: Message, state: FSMContext):
    """Добавляем ещё одно занятие"""
    await state.set_state(ManualSessionStates.waiting_for_date)
    await message.answer(
        "📝 **Новое занятие**\n\n"
        "Введи **дату** экзамена:"
    )


@router.message(ManualSessionStates.waiting_for_more, Command("ready"))
async def finish_manual_input(message: Message, state: FSMContext):
    """Завершаем ввод и показываем предпросмотр"""
    data = await state.get_data()
    sessions = data.get('sessions', [])

    if not sessions:
        await message.answer("❌ Нет добавленных занятий. Ввод отменён.")
        await state.clear()
        return

    # Переходим к предпросмотру и подтверждению
    await state.update_data(sessions=sessions)
    await state.set_state(SessionImportStates.waiting_for_confirmation)

    # Показываем предпросмотр
    response = "📋 **Предпросмотр расписания:**\n\n"
    current_date = None

    for session in sessions:
        date_display = session['date'].strftime("%d.%m.%Y")

        if date_display != current_date:
            current_date = date_display
            response += f"\n📅 **{date_display}**\n"

        response += f"   ⏰ {session['start_time']}"
        if session.get('end_time'):
            response += f" - {session['end_time']}"
        response += f"\n   📚 Предмет: {session['subject_name']}\n"
        if session.get('classroom'):
            response += f"   🏛 Аудитория: {session['classroom']}\n"
        response += "\n"

    await message.answer(response)
    await message.answer(
        "❓ **Всё верно?**\n\n"
        "✅ /confirm - сохранить расписание\n"
        "❌ /cancel - отменить импорт\n\n"
        "Если хочешь добавить ещё - используй /add"
    )


@router.message(ManualSessionStates.waiting_for_more, Command("cancel"))
async def cancel_manual_input(message: Message, state: FSMContext):
    """Отмена ручного ввода"""
    await state.clear()
    await message.answer("❌ Ручной ввод отменён. Все данные удалены.")


# Общий обработчик отмены для всех состояний
@router.message(Command("cancel"))
async def cancel_all(message: Message, state: FSMContext):
    current_state = await state.get_state()

    # Очищаем состояние
    await state.clear()

    # Если были временные файлы, удаляем их
    data = await state.get_data()
    temp_path = data.get('temp_path')
    if temp_path and os.path.exists(temp_path):
        os.remove(temp_path)

    await message.answer(
        "❌ Действие отменено.\n\n"
        "Можешь начать заново командой /import_session"
    )


@router.message(F.document)
async def handle_document(message: Message, state: FSMContext):
    if not message.document.file_name.endswith('.xlsx'):
        await message.answer("❌ Пожалуйста, отправьте файл в формате .xlsx")
        return

    file_info = await message.bot.get_file(message.document.file_id)
    downloaded_file = await message.bot.download_file(file_info.file_path)

    temp_path = f"temp_{message.document.file_name}"
    with open(temp_path, "wb") as f:
        f.write(downloaded_file.getvalue())

    await message.answer("📥 Файл получен. Обрабатываю...")

    sessions = parse_excel_schedule(temp_path)

    if sessions:
        response = "📋 **Предпросмотр расписания:**\n\n"
        current_date = None

        for session in sessions:
            if session['date'] != current_date:
                current_date = session['date']
                response += f"\n📅 **{current_date}**\n"

            response += f"   ⏰ {session['start_time']}\n"
            response += f"   📚 Предмет: {session['subject_name']}\n"
            response += f"   🏛 Аудитория: {session.get('classroom', 'не указана')}\n\n"

        await state.update_data(sessions=sessions, temp_path=temp_path)
        await state.set_state(SessionImportStates.waiting_for_confirmation)

        await message.answer(response)
        await message.answer(
            "❓ **Всё верно?**\n\n"
            "✅ /confirm - сохранить расписание\n"
            "❌ /cancel - отменить импорт"
        )
    else:
        await message.answer("❌ Не удалось распознать расписание. Проверьте формат файла.")
        os.remove(temp_path)


@router.message(Command("confirm"))
async def confirm_schedule(message: Message, state: FSMContext):
    data = await state.get_data()
    sessions = data.get('sessions')
    temp_path = data.get('temp_path')

    if not sessions:
        await message.answer("❌ Нет данных для сохранения. Попробуйте загрузить файл заново.")
        await state.clear()
        return

    # Получаем информацию о пользователе из БД
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()

    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start")
        close_db(db)
        await state.clear()
        return

    user_db_id = user.id
    group_id = user.group_id  # если есть группа, иначе None

    close_db(db)

    saved_count = 0
    errors = []

    db = get_db()
    for session in sessions:
        subject = db.query(Subject).filter(
            Subject.name == session['subject_name'],
            Subject.user_id == user_db_id
        ).first()

        if not subject:
            errors.append(f"Предмет '{session['subject_name']}' не найден")
            continue

        subject_id = subject.id
        try:
            result = create_session_schedule(
                group_id=group_id,  # ID группы (или None для личного)
                user_id=user_db_id,  # ID пользователя (или None для группы)
                subject_id=subject_id,  # ID предмета (нужно получить!)
                date=session['date'],  # дата (datetime объект)
                start_time=session['start_time'],  # "09:00"
                end_time=session.get('end_time', ""),  # время окончания (если есть)
                classroom=session.get('classroom', "")  # аудитория
            )
            saved_count += 1

        except Exception as e:
            errors.append(f"{session.get('subject_name')}: {e}")

    close_db(db)

    # Очищаем временные файлы
    if temp_path and os.path.exists(temp_path):
        os.remove(temp_path)

    if errors:
        await message.answer(
            f"⚠️ Частично сохранено: {saved_count}/{len(sessions)}\n\n"
            f"Ошибки:\n" + "\n".join(errors[:5])
        )
    else:
        await message.answer(
            f"✅ **Расписание успешно сохранено!**\n\n"
            f"📊 Добавлено занятий: {saved_count}"
        )

    await state.clear()


@router.message(Command('cancel'))
async def cancel_import(message: Message, state: FSMContext):
    data = await state.get_data()
    temp_path = data.get('temp_path')

    if temp_path and os.path.exists(temp_path):
        os.remove(temp_path)

    await state.clear()
    await message.answer("❌ Импорт отменён.")


@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext):
    await message.answer("📸 Фото получено. Начинаю распознавание текста...\n⏳ Это может занять 10-30 секунд")

    photo = message.photo[-1]
    file_info = await message.bot.get_file(photo.file_id)

    temp_path = f"temp_photo_{message.message_id}.jpg"
    await message.bot.download_file(file_info.file_path, temp_path)

    try:
        recognized_text = ocr_photo(temp_path)

        if recognized_text:
            await message.answer(f"📝 Распознанный текст:\n\n{recognized_text[:500]}")

            parsed_exams = parse_schedule_from_photo(recognized_text)

            if parsed_exams:
                sessions = []

                for exam in parsed_exams:
                    # Обработка даты
                    date_value = exam.get('date') or exam.get('day')
                    if isinstance(date_value, str):
                        try:
                            for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%Y.%m.%d"]:
                                try:
                                    date_value = datetime.strptime(date_value, fmt)
                                    break
                                except ValueError:
                                    continue
                        except:
                            date_value = None

                    session_data = {
                        'date': date_value,
                        'start_time': exam.get('start_time', ''),
                        'subject_name': exam.get('subject', exam.get('subject_name', '')),
                        'classroom': exam.get('classroom', exam.get('auditorium', ''))
                    }
                    sessions.append(session_data)  # ← Добавляем КАЖДЫЙ экзамен

                # Показываем предпросмотр
                response = "📋 **Предпросмотр расписания:**\n\n"
                current_date = None

                for session in sessions:
                    date_display = session['date'].strftime("%d.%m.%Y") if isinstance(session['date'], datetime) else \
                        session['date']

                    if date_display != current_date:
                        current_date = date_display
                        response += f"\n📅 **{date_display}**\n"

                    response += f"   ⏰ {session['start_time']}\n"
                    response += f"   📚 Предмет: {session['subject_name']}\n"
                    response += f"   🏛 Аудитория: {session.get('classroom', 'не указана')}\n\n"

                await state.update_data(sessions=sessions, temp_path=temp_path)
                await state.set_state(SessionImportStates.waiting_for_confirmation)

                await message.answer(response)
                await message.answer(
                    "❓ **Всё верно?**\n\n"
                    "✅ /confirm - сохранить\n"
                    "❌ /cancel - отменить"
                )
            else:
                await message.answer(
                    "⚠️ Не удалось распознать структуру расписания.\n\n"
                    f"Распознанный текст:\n{recognized_text[:300]}\n\n"
                    "Проверь формат фото или используй Excel файл."
                )
        else:
            await message.answer(
                "❌ Не удалось распознать текст на фото.\n\n"
                "Попробуй:\n"
                "- Сделать фото более четким\n"
                "- Улучшить освещение\n"
                "- Использовать Excel файл"
            )

    except Exception as e:
        await message.answer(f"❌ Ошибка при распознавании: {e}")

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
