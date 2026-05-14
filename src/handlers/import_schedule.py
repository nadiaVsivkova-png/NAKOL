import os
from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile, \
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from parsers.excel_parser import parse_excel_schedule
from parsers.photo_parser import ocr_photo, parse_schedule_from_photo
from database.db import get_db, close_db
from database.models import User, Subject
from datetime import datetime
from database.group_functions import get_or_create_subject
from database.db import create_schedule

router = Router()


def can_import_schedule(user) -> tuple:
    """
    Проверяет, может ли пользователь импортировать расписание.
    Возвращает (can_import, message)
    """
    if user.role == "starosta" and user.group_id:
        # Староста может импортировать расписание для группы
        return True, None
    elif user.role == "student":
        # Студент может импортировать только если он НЕ в группе
        if user.group_id:
            return False, "❌ Вы состоите в группе. Расписание загружает староста.\n\nОбратитесь к старосте вашей группы."
        else:
            return True, None
    else:
        return True, None


# ==================== FSM СОСТОЯНИЯ ДЛЯ ИМПОРТА РАСПИСАНИЯ ====================
class ScheduleImportStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_excel = State()


# ==================== FSM СОСТОЯНИЯ ДЛЯ ПОДТВЕРЖДЕНИЯ ====================
class ScheduleConfirmStates(StatesGroup):
    waiting_for_confirmation = State()


# ==================== FSM СОСТОЯНИЯ ДЛЯ РУЧНОГО ВВОДА ====================
class ScheduleManualStates(StatesGroup):
    waiting_for_day = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()
    waiting_for_subject = State()
    waiting_for_week_type = State()
    waiting_for_classroom = State()
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


def get_week_type_keyboard():
    """Клавиатура для выбора типа недели"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Каждая неделя", callback_data="week_both"),
            InlineKeyboardButton(text="📆 Чётная неделя", callback_data="week_even")
        ],
        [
            InlineKeyboardButton(text="📆 Нечётная неделя", callback_data="week_odd"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="week_cancel")
        ]
    ])
    return keyboard


def get_next_action_keyboard():
    """Клавиатура для выбора: добавить ещё или завершить"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ещё занятие", callback_data="schedule_add_more")],
        [InlineKeyboardButton(text="✅ Завершить и сохранить всё", callback_data="schedule_finish")]
    ])
    return keyboard


# ==================== КОМАНДА /import_schedule ====================
@router.message(Command("import_schedule"))
async def import_schedule(message: Message, state: FSMContext):
    # Проверка пользователя
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    can_import, error_msg = can_import_schedule(user)
    if not can_import:
        await message.answer(error_msg)
        return

    await message.answer("Каким способом хочешь импортировать расписание?",
                         reply_markup=schedule_keyboard)


# ==================== EXCEL ====================
@router.message(F.text == "📊Загрузить Excel-файл(рекомендую)")
async def handle_excel(message: Message, state: FSMContext):
    # Проверка пользователя
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    can_import, error_msg = can_import_schedule(user)
    if not can_import:
        await message.answer(error_msg)
        return

    await state.set_state(ScheduleImportStates.waiting_for_excel)
    await message.answer("Ты выбрал Excel-файл. Скачай шаблон и заполни его: /template\n\n"
                         "После заполнения просто загрузи файл сюда.",
                         reply_markup=ReplyKeyboardRemove())


@router.message(Command("template"))
async def answer_download(message: Message):
    template_path = "../templates/schedule_template.xlsx"

    if os.path.exists(template_path):
        file = FSInputFile(template_path)
        await message.answer_document(
            document=file,
            caption="📋 Шаблон расписания\n\n"
                    "Заполни файл и отправь его обратно. "
                    "Не меняй название файла!\n\n"
        )
    else:
        await message.answer("❌ Шаблон не найден.")


# ==================== ОБРАБОТЧИК EXCEL ФАЙЛА С ПРЕДПРОСМОТРОМ ====================
@router.message(ScheduleImportStates.waiting_for_excel, F.document)
async def handle_document(message: Message, state: FSMContext):
    if not (message.document.file_name.startswith("schedule") and message.document.file_name.endswith(".xlsx")):
        await message.answer(
            "❌ Неверный формат файла.\n\n"
            "Файл должен:\n"
            "• Начинаться с 'schedule'\n"
            "• Иметь расширение .xlsx\n\n"
            "Пример: schedule.xlsx"
        )
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

    # Сохраняем распарсенные уроки в состояние
    await state.update_data(pending_lessons=lessons)

    # Формируем сообщение с предпросмотром
    preview_text = "📋 **Предпросмотр расписания:**\n\n"

    for i, lesson in enumerate(lessons, 1):
        preview_text += f"{i}. 📅 {lesson['day']} | ⏰ {lesson['start_time']}-{lesson['end_time']}\n"
        preview_text += f"   📚 {lesson['subject']}\n"

        week_type_text = {
            "both": "📆 Каждая неделя",
            "even": "📆 Чётная неделя",
            "odd": "📆 Нечётная неделя"
        }.get(lesson.get('week_type', 'both'), lesson.get('week_type', 'both'))
        preview_text += f"   {week_type_text}\n"

        if lesson.get('classroom'):
            preview_text += f"   🏛 Аудитория: {lesson['classroom']}\n"

        preview_text += "\n"

    # Ограничиваем длину сообщения (Telegram лимит ~4096 символов)
    if len(preview_text) > 3800:
        preview_text = preview_text[:3800] + "\n\n... и ещё несколько занятий"

    # Клавиатура для подтверждения
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, всё верно", callback_data="schedule_confirm_yes")],
        [InlineKeyboardButton(text="❌ Нет, отменить", callback_data="schedule_confirm_no")],
        [InlineKeyboardButton(text="📝 Ввести вручную", callback_data="schedule_confirm_manual")]
    ])

    await state.set_state(ScheduleConfirmStates.waiting_for_confirmation)
    await message.answer(
        preview_text,
        reply_markup=confirm_keyboard,
        parse_mode="Markdown"
    )


# ==================== ОБРАБОТЧИКИ ПОДТВЕРЖДЕНИЯ ====================

@router.callback_query(ScheduleConfirmStates.waiting_for_confirmation, F.data == "schedule_confirm_yes")
async def confirm_schedule(callback: CallbackQuery, state: FSMContext):
    """Сохраняем расписание после подтверждения"""
    data = await state.get_data()
    lessons = data.get('pending_lessons', [])

    if not lessons:
        await callback.message.edit_text("❌ Нет данных для сохранения.")
        await state.clear()
        await callback.answer()
        return

    await callback.message.edit_text("💾 Сохраняю расписание...")

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(callback.from_user.id)).first()

    saved_count = 0
    errors = []

    for i, lesson in enumerate(lessons, 1):
        try:
            if user.role == "starosta" and user.group_id:
                subject_id = get_or_create_subject(lesson['subject'], group_id=user.group_id)
                group_id = user.group_id
                user_id = None
            else:
                subject_id = get_or_create_subject(lesson['subject'], user_id=user.id)
                group_id = None
                user_id = user.id

            if subject_id is None:
                errors.append(f"Занятие {i}: не удалось создать предмет «{lesson['subject']}»")
                continue

            create_schedule(
                group_id=group_id,
                user_id=user_id,
                subject_id=subject_id,
                weekday=lesson['day'],
                start_time=lesson['start_time'],
                end_time=lesson['end_time'],
                week_type=lesson.get('week_type', 'both'),
                classroom=lesson.get('classroom', "")
            )
            saved_count += 1
        except Exception as e:
            errors.append(f"Занятие {i}: {str(e)}")

    close_db(db)

    result_text = f"✅ Расписание сохранено!\n\n📊 Добавлено занятий: {saved_count}/{len(lessons)}"

    if errors:
        result_text += f"\n\n⚠️ Ошибки:\n" + "\n".join(errors[:5])
        if len(errors) > 5:
            result_text += f"\n... и ещё {len(errors) - 5} ошибок"

    await callback.message.edit_text(result_text)
    await state.clear()
    await callback.answer()


@router.callback_query(ScheduleConfirmStates.waiting_for_confirmation, F.data == "schedule_confirm_no")
async def cancel_schedule(callback: CallbackQuery, state: FSMContext):
    """Отменяем сохранение"""
    await callback.message.edit_text(
        "❌ Импорт отменён.\n\n"
        "Ты можешь:\n"
        "• Загрузить исправленный файл\n"
        "• Использовать /import_schedule для нового импорта\n"
        "• Ввести расписание вручную"
    )
    await state.clear()
    await callback.answer()


@router.callback_query(ScheduleConfirmStates.waiting_for_confirmation, F.data == "schedule_confirm_manual")
async def switch_to_manual(callback: CallbackQuery, state: FSMContext):
    """Переключаемся на ручной ввод"""
    await callback.message.edit_text("🔄 Переключаюсь на ручной ввод...")
    await state.clear()

    # Запускаем ручной ввод
    await state.update_data(lessons=[])
    await state.set_state(ScheduleManualStates.waiting_for_day)

    await callback.message.answer(
        "📝 Пошаговый ввод расписания\n\n"
        "Введи день недели в формате:\n"
        "• пн\n• вт\n• ср\n• чт\n• пт\n• сб\n• вс\n\n❌ /cancel - отменить",
        reply_markup=ReplyKeyboardRemove()
    )
    await callback.answer()


# ==================== ФОТО (OCR) ====================
@router.message(F.text == "📸Отправить фото(распознаю текст)")
async def handle_photo_schedule(message: Message, state: FSMContext):
    # Проверка пользователя
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    can_import, error_msg = can_import_schedule(user)
    if not can_import:
        await message.answer(error_msg)
        return

    await state.set_state(ScheduleImportStates.waiting_for_photo)
    await message.answer(
        "📸 Отправь фото расписания. Важно: фото должно быть чётким.\n"
        "Пример в каком формате должно быть расписание на фото:\n"
        "понедельник 09:00-10:30 Математика\n"
        "вторник 10:45-12:15 Физика even\n"
        "итд.. (представь, что ты заскринил этот текст :))"
        "❌ /cancel - отменить",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(ScheduleImportStates.waiting_for_photo, F.photo)
async def process_photo_schedule(message: Message, state: FSMContext):
    await message.answer("📸 Фото получено. Распознаю текст...")

    photo = message.photo[-1]
    file_info = await message.bot.get_file(photo.file_id)

    temp_path = f"temp_photo_{message.message_id}.jpg"
    await message.bot.download_file(file_info.file_path, temp_path)

    try:
        recognized_text = ocr_photo(temp_path)

        if not recognized_text:
            await message.answer("❌ Текст не распознан")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return

        await message.answer(f"📝 OCR распознал:\n\n{recognized_text[:500]}")

        lessons = parse_schedule_from_photo(recognized_text)

        if not lessons:
            await message.answer("❌ Не удалось распознать расписание")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return

        # Сохраняем распарсенные уроки и путь к фото в состояние
        await state.update_data(pending_lessons=lessons, temp_photo_path=temp_path)

        # Формируем сообщение с предпросмотром
        preview_text = "📋 **Предпросмотр расписания:**\n\n"

        for i, lesson in enumerate(lessons, 1):
            preview_text += f"{i}. 📅 {lesson['day']} | ⏰ {lesson['start_time']}-{lesson['end_time']}\n"
            preview_text += f"   📚 {lesson['subject']}\n"

            week_type_text = {
                "both": "📆 Каждая неделя",
                "even": "📆 Чётная неделя",
                "odd": "📆 Нечётная неделя"
            }.get(lesson.get('week_type', 'both'), lesson.get('week_type', 'both'))
            preview_text += f"   {week_type_text}\n"

            if lesson.get('classroom'):
                preview_text += f"   🏛 Аудитория: {lesson['classroom']}\n"

            preview_text += "\n"

        # Ограничиваем длину сообщения
        if len(preview_text) > 3800:
            preview_text = preview_text[:3800] + "\n\n... и ещё несколько занятий"

        # Клавиатура для подтверждения
        confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, всё верно", callback_data="schedule_confirm_yes")],
            [InlineKeyboardButton(text="❌ Нет, отменить", callback_data="schedule_confirm_no")],
            [InlineKeyboardButton(text="📝 Ввести вручную", callback_data="schedule_confirm_manual")]
        ])

        await state.set_state(ScheduleConfirmStates.waiting_for_confirmation)
        await message.answer(
            preview_text,
            reply_markup=confirm_keyboard,
            parse_mode="Markdown"
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка при распознавании: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ==================== РУЧНОЙ ВВОД ====================
@router.message(F.text == "✍️Ввести расписание вручную")
async def start_manual_input(message: Message, state: FSMContext):
    # Проверка пользователя
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    can_import, error_msg = can_import_schedule(user)
    if not can_import:
        await message.answer(error_msg)
        return

    await state.clear()
    await state.update_data(lessons=[])
    await state.set_state(ScheduleManualStates.waiting_for_day)

    await message.answer(
        "📝 Пошаговый ввод расписания\n\n"
        "Введи день недели в формате:\n"
        "• пн\n• вт\n• ср\n• чт\n• пт\n• сб\n• вс\n\n❌ /cancel - отменить",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(ScheduleManualStates.waiting_for_day)
async def process_day(message: Message, state: FSMContext):
    # Проверяем на команду отмены
    if message.text and message.text.startswith('/cancel'):
        await cancel_manual(message, state)
        return

    # Игнорируем другие команды
    if message.text and message.text.startswith('/'):
        return

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
    await message.answer(f"✅ День: {day}\n\nТеперь введи время начала (например: 09:00):")


@router.message(ScheduleManualStates.waiting_for_start_time)
async def process_start_time(message: Message, state: FSMContext):
    # Проверяем на команду отмены
    if message.text and message.text.startswith('/cancel'):
        await cancel_manual(message, state)
        return

    # Игнорируем другие команды
    if message.text and message.text.startswith('/'):
        return

    time_str = message.text.strip()
    try:
        start_time = datetime.strptime(time_str, "%H:%M").strftime("%H:%M")
    except ValueError:
        await message.answer("❌ Неверный формат. Пример: 09:00")
        return

    await state.update_data(temp_start_time=start_time)
    await state.set_state(ScheduleManualStates.waiting_for_end_time)
    await message.answer(f"✅ Время начала: {start_time}\n\nТеперь введи время окончания (например: 10:30):")


@router.message(ScheduleManualStates.waiting_for_end_time)
async def process_end_time(message: Message, state: FSMContext):
    # Проверяем на команду отмены
    if message.text and message.text.startswith('/cancel'):
        await cancel_manual(message, state)
        return

    # Игнорируем другие команды
    if message.text and message.text.startswith('/'):
        return

    time_str = message.text.strip()
    try:
        end_time = datetime.strptime(time_str, "%H:%M").strftime("%H:%M")
    except ValueError:
        await message.answer("❌ Неверный формат. Пример: 10:30")
        return

    await state.update_data(temp_end_time=end_time)
    await state.set_state(ScheduleManualStates.waiting_for_subject)
    await message.answer(f"✅ Время окончания: {end_time}\n\nТеперь введи название предмета:")


@router.message(ScheduleManualStates.waiting_for_subject)
async def process_subject(message: Message, state: FSMContext):
    # Проверяем на команду отмены
    if message.text and message.text.startswith('/cancel'):
        await cancel_manual(message, state)
        return

    # Игнорируем другие команды
    if message.text and message.text.startswith('/'):
        return

    subject_name = message.text.strip()

    if not subject_name:
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
        await message.answer(f"❌ Не удалось создать предмет {subject_name}")
        return

    await state.update_data(temp_subject_id=subject_id, temp_subject_name=subject_name)
    await state.set_state(ScheduleManualStates.waiting_for_week_type)

    await message.answer(
        "📅 Выбери тип недели для этого предмета:",
        reply_markup=get_week_type_keyboard()
    )


# ==================== ОБРАБОТЧИКИ ВЫБОРА ТИПА НЕДЕЛИ ====================

@router.callback_query(F.data == "week_both")
async def set_week_both(callback: CallbackQuery, state: FSMContext):
    await state.update_data(temp_week_type="both")
    await state.set_state(ScheduleManualStates.waiting_for_classroom)
    await callback.message.edit_text("✅ Предмет будет на каждой неделе\n\nТеперь введи аудиторию (или отправь /skip):")
    await callback.answer()


@router.callback_query(F.data == "week_even")
async def set_week_even(callback: CallbackQuery, state: FSMContext):
    await state.update_data(temp_week_type="even")
    await state.set_state(ScheduleManualStates.waiting_for_classroom)
    await callback.message.edit_text(
        "✅ Предмет будет только в чётную неделю\n\nТеперь введи аудиторию (или отправь /skip):")
    await callback.answer()


@router.callback_query(F.data == "week_odd")
async def set_week_odd(callback: CallbackQuery, state: FSMContext):
    await state.update_data(temp_week_type="odd")
    await state.set_state(ScheduleManualStates.waiting_for_classroom)
    await callback.message.edit_text(
        "✅ Предмет будет только в нечётную неделю\n\nТеперь введи аудиторию (или отправь /skip):")
    await callback.answer()


@router.callback_query(F.data == "week_cancel")
async def cancel_week_type(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Ввод отменён. Используй /import_schedule чтобы начать заново")
    await state.clear()
    await callback.answer()


@router.message(ScheduleManualStates.waiting_for_classroom)
async def process_classroom(message: Message, state: FSMContext):
    # Проверяем на команду отмены
    if message.text and message.text.startswith('/cancel'):
        await cancel_manual(message, state)
        return

    if message.text == "/skip":
        classroom = ""
    else:
        # Игнорируем другие команды
        if message.text and message.text.startswith('/'):
            return
        classroom = message.text.strip()

    data = await state.get_data()
    new_lesson = {
        'day': data.get('temp_day'),
        'start_time': data.get('temp_start_time'),
        'end_time': data.get('temp_end_time'),
        'subject_name': data.get('temp_subject_name'),
        'subject_id': data.get('temp_subject_id'),
        'week_type': data.get('temp_week_type', 'both'),
        'classroom': classroom
    }

    lessons = data.get('lessons', [])
    lessons.append(new_lesson)
    await state.update_data(lessons=lessons)

    await state.update_data(
        temp_day=None,
        temp_start_time=None,
        temp_end_time=None,
        temp_subject_id=None,
        temp_subject_name=None,
        temp_week_type=None
    )

    response = f"✅ Добавлено занятие №{len(lessons)}:\n\n"
    response += f"   📅 День: {new_lesson['day']}\n"
    response += f"   ⏰ Время: {new_lesson['start_time']} - {new_lesson['end_time']}\n"
    response += f"   📚 Предмет: {new_lesson['subject_name']}\n"

    week_type_text = {
        "both": "Каждая неделя",
        "even": "Только чётная неделя",
        "odd": "Только нечётная неделя"
    }.get(new_lesson['week_type'], new_lesson['week_type'])
    response += f"   📆 {week_type_text}\n"

    if classroom:
        response += f"   🏛 Аудитория: {classroom}\n"

    await message.answer(response)

    await state.set_state(ScheduleManualStates.waiting_for_more)
    await message.answer(
        "❓ Что дальше?\n\n"
        "✅ /add - добавить ещё одно занятие\n"
        "✅ /ready - завершить и сохранить\n"
        "❌ /cancel - отменить"
    )


@router.message(ScheduleManualStates.waiting_for_more, Command("add"))
async def add_more(message: Message, state: FSMContext):
    await state.set_state(ScheduleManualStates.waiting_for_day)
    await message.answer("Введи день недели для нового занятия:")


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

        create_schedule(
            group_id=group_id,
            user_id=user_id,
            subject_id=lesson['subject_id'],
            weekday=lesson['day'],
            start_time=lesson['start_time'],
            end_time=lesson['end_time'],
            week_type=lesson.get('week_type', 'both'),
            classroom=lesson.get('classroom', "")
        )
        saved_count += 1

    await message.answer(f"✅ Расписание сохранено!\n\n📊 Добавлено занятий: {saved_count}")
    await state.clear()


@router.message(ScheduleManualStates.waiting_for_more, Command("cancel"))
async def cancel_manual(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Ручной ввод отменён.")


# ==================== ОТМЕНА ====================
@router.message(Command("cancel"))
async def cancel_all(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=ReplyKeyboardRemove())


@router.callback_query(ScheduleConfirmStates.waiting_for_confirmation, F.data == "schedule_confirm_yes")
async def confirm_schedule(callback: CallbackQuery, state: FSMContext):
    """Сохраняем расписание после подтверждения"""
    data = await state.get_data()
    lessons = data.get('pending_lessons', [])
    temp_photo_path = data.get('temp_photo_path')  # Добавлено

    if not lessons:
        await callback.message.edit_text("❌ Нет данных для сохранения.")
        await state.clear()
        await callback.answer()
        return

    await callback.message.edit_text("💾 Сохраняю расписание...")

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(callback.from_user.id)).first()

    saved_count = 0
    errors = []

    for i, lesson in enumerate(lessons, 1):
        try:
            if user.role == "starosta" and user.group_id:
                subject_id = get_or_create_subject(lesson['subject'], group_id=user.group_id)
                group_id = user.group_id
                user_id = None
            else:
                subject_id = get_or_create_subject(lesson['subject'], user_id=user.id)
                group_id = None
                user_id = user.id

            if subject_id is None:
                errors.append(f"Занятие {i}: не удалось создать предмет «{lesson['subject']}»")
                continue

            create_schedule(
                group_id=group_id,
                user_id=user_id,
                subject_id=subject_id,
                weekday=lesson['day'],
                start_time=lesson['start_time'],
                end_time=lesson['end_time'],
                week_type=lesson.get('week_type', 'both'),
                classroom=lesson.get('classroom', "")
            )
            saved_count += 1
        except Exception as e:
            errors.append(f"Занятие {i}: {str(e)}")

    close_db(db)

    # Удаляем временный файл
    if temp_photo_path and os.path.exists(temp_photo_path):
        os.remove(temp_photo_path)

    result_text = f"✅ Расписание сохранено!\n\n📊 Добавлено занятий: {saved_count}/{len(lessons)}"

    if errors:
        result_text += f"\n\n⚠️ Ошибки:\n" + "\n".join(errors[:5])
        if len(errors) > 5:
            result_text += f"\n... и ещё {len(errors) - 5} ошибок"

    await callback.message.edit_text(result_text)
    await state.clear()
    await callback.answer()


@router.callback_query(ScheduleConfirmStates.waiting_for_confirmation, F.data == "schedule_confirm_no")
async def cancel_schedule(callback: CallbackQuery, state: FSMContext):
    """Отменяем сохранение"""
    data = await state.get_data()
    temp_photo_path = data.get('temp_photo_path')

    if temp_photo_path and os.path.exists(temp_photo_path):
        os.remove(temp_photo_path)

    await callback.message.edit_text(
        "❌ Импорт отменён.\n\n"
        "Ты можешь:\n"
        "• Загрузить исправленный файл\n"
        "• Использовать /import_schedule для нового импорта\n"
        "• Ввести расписание вручную"
    )
    await state.clear()
    await callback.answer()
