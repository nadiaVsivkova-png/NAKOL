from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, \
    InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import get_db, close_db
from database.models import User, Subject
from database.group_functions import create_task
from datetime import datetime

router = Router()


# Состояния для FSM
class HomeworkImportStates(StatesGroup):
    # Для фото
    waiting_for_photo = State()  # ожидаем фото
    waiting_for_photo_subject = State()  # ожидаем предмет (для фото)
    waiting_for_photo_deadline = State()  # ожидаем дедлайн (для фото)

    # Для ручного ввода
    waiting_for_manual_subject = State()  # ожидаем предмет (для ручного)
    waiting_for_task_text = State()  # ожидаем текст задания (для ручного)
    waiting_for_manual_deadline = State()  # ожидаем дедлайн (для ручного)

    # Общее
    waiting_for_next_action = State()  # ожидаем решение: добавить ещё или завершить


# Клавиатура выбора способа
homework_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📸 Отправить фото")],
        [KeyboardButton(text="✍️ Введу вручную задания")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


def get_next_action_keyboard():
    """Клавиатура для выбора: добавить ещё или завершить"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ещё задание", callback_data="homework_add_more")],
        [InlineKeyboardButton(text="✅ Завершить и сохранить всё", callback_data="homework_finish")]
    ])
    return keyboard


@router.message(Command("import_homework"))
async def import_homework(message: Message, state: FSMContext):
    """Начинаем импорт домашнего задания"""
    await state.clear()
    await state.update_data(homeworks=[])
    await message.answer(
        "📚 **Импорт домашнего задания**\n\n"
        "Выбери способ:",
        reply_markup=homework_keyboard
    )


@router.message(F.text == "📸 Отправить фото")
async def handle_photo_method(message: Message, state: FSMContext):
    """Обработчик выбора способа 'Отправить фото'"""
    await state.set_state(HomeworkImportStates.waiting_for_photo)
    await message.answer(
        "📸 Отправь фото домашнего задания.\n\n"
        "Фото будет сохранено как условие задачи.\n\n"
        "❌ /cancel - отменить",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(HomeworkImportStates.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    """Получаем фото и сохраняем file_id"""
    photo = message.photo[-1]
    photo_file_id = photo.file_id

    await state.update_data(temp_photo_file_id=photo_file_id)
    await state.set_state(HomeworkImportStates.waiting_for_photo_subject)

    await message.answer(
        "✅ Фото получено и сохранено!\n\n"
        "Теперь введи **название предмета**:\n\n"
        "❌ /cancel - отменить"
    )


@router.message(HomeworkImportStates.waiting_for_photo)
async def invalid_photo(message: Message):
    """Если отправили не фото"""
    await message.answer(
        "❌ Пожалуйста, отправь **фото**.\n\n"
        "Или используй /cancel для отмены."
    )


@router.message(HomeworkImportStates.waiting_for_photo_subject)
async def process_photo_subject(message: Message, state: FSMContext):
    """Получаем название предмета для фото"""
    subject_name = message.text.strip()

    if not subject_name or subject_name.startswith('/'):
        await message.answer("❌ Введи корректное название предмета:")
        return

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()


    subject = db.query(Subject).filter(
        Subject.name == subject_name,
        Subject.user_id == user.id
    ).first()

    if not subject:
        await message.answer(
            f"❌ Предмет «{subject_name}» не найден.\n\n"
            f"Введи другое название:"
        )
        close_db(db)
        return

    close_db(db)

    await state.update_data(temp_subject_id=subject.id, temp_subject_name=subject.name)
    await state.set_state(HomeworkImportStates.waiting_for_photo_deadline)

    await message.answer(
        f"✅ Предмет: {subject.name}\n\n"
        "Теперь введи **дедлайн** в формате:\n"
        "• ДД.ММ.ГГГГ (например: 25.12.2026)\n"
        "• ДД.ММ.ГГ (например: 25.12.26)\n\n"
        "❌ /cancel - отменить"
    )


@router.message(HomeworkImportStates.waiting_for_photo_deadline)
async def process_photo_deadline(message: Message, state: FSMContext):
    """Получаем дедлайн и сохраняем задание с фото"""
    deadline_str = message.text.strip()

    date_formats = ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y"]
    deadline = None

    for fmt in date_formats:
        try:
            deadline = datetime.strptime(deadline_str, fmt)
            break
        except ValueError:
            continue

    if deadline is None:
        await message.answer(
            "❌ Неверный формат даты.\n\n"
            "Попробуй ещё раз (например: 25.12.2026):\n\n"
            "❌ /cancel - отменить"
        )
        return

    data = await state.get_data()
    temp_photo_file_id = data.get('temp_photo_file_id')
    temp_subject_id = data.get('temp_subject_id')
    temp_subject_name = data.get('temp_subject_name')

    # Текст задания = "Домашнее задание" (или можно оставить пустым)
    task_text = "Домашнее задание"  # текст по умолчанию, т.к. задание в фото

    new_homework = {
        'subject_id': temp_subject_id,
        'subject_name': temp_subject_name,
        'task_text': task_text,
        'deadline': deadline,
        'photo_file_id': temp_photo_file_id
    }

    homeworks = data.get('homeworks', [])
    homeworks.append(new_homework)
    await state.update_data(homeworks=homeworks)

    await state.update_data(
        temp_photo_file_id=None,
        temp_subject_id=None,
        temp_subject_name=None
    )

    # Показываем предпросмотр с фото
    response = f"✅ **Задание добавлено в список!**\n\n"
    response += f"📚 Предмет: {temp_subject_name}\n"
    response += f"📅 Дедлайн: {deadline.strftime('%d.%m.%Y')}\n"
    response += f"📸 Фото: прикреплено (условие задачи)\n"

    await message.answer_photo(photo=temp_photo_file_id, caption=response)

    await state.set_state(HomeworkImportStates.waiting_for_next_action)
    await message.answer(
        f"📊 **В списке сейчас {len(homeworks)} заданий.**\n\n"
        "Что хочешь сделать?",
        reply_markup=get_next_action_keyboard()
    )


@router.message(F.text == "✍️ Введу вручную задания")
async def handle_manual_method(message: Message, state: FSMContext):
    """Обработчик выбора способа 'Ввести вручную'"""
    await state.update_data(temp_photo_file_id=None)
    await state.set_state(HomeworkImportStates.waiting_for_manual_subject)
    await message.answer(
        "✍️ **Ручной ввод задания**\n\n"
        "Введи **название предмета**:\n\n"
        "❌ /cancel - отменить",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(HomeworkImportStates.waiting_for_manual_subject)
async def process_manual_subject(message: Message, state: FSMContext):
    """Получаем название предмета для ручного ввода"""
    subject_name = message.text.strip()

    if not subject_name or subject_name.startswith('/'):
        await message.answer("❌ Введи корректное название предмета:")
        return

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()

    if not user:
        await message.answer("❌ Ты не зарегистрирован. Используй /start")
        close_db(db)
        await state.clear()
        return

    subject = db.query(Subject).filter(
        Subject.name == subject_name,
        Subject.user_id == user.id
    ).first()

    if not subject:
        await message.answer(
            f"❌ Предмет «{subject_name}» не найден.\n\n"
            f"Введи другое название:"
        )
        close_db(db)
        return

    close_db(db)

    await state.update_data(temp_subject_id=subject.id, temp_subject_name=subject.name)
    await state.set_state(HomeworkImportStates.waiting_for_task_text)

    await message.answer(
        f"✅ Предмет: {subject.name}\n\n"
        "Теперь введи **текст задания** (что нужно сделать):\n\n"
        "❌ /cancel - отменить"
    )


@router.message(HomeworkImportStates.waiting_for_task_text)
async def process_task_text(message: Message, state: FSMContext):
    """Получаем текст задания для ручного ввода"""
    task_text = message.text.strip()

    if not task_text or task_text.startswith('/'):
        await message.answer("❌ Введи корректный текст задания:")
        return

    await state.update_data(temp_task_text=task_text)
    await state.set_state(HomeworkImportStates.waiting_for_manual_deadline)

    await message.answer(
        f"✅ Текст задания: {task_text[:100]}{'...' if len(task_text) > 100 else ''}\n\n"
        "Теперь введи **дедлайн** в формате:\n"
        "• ДД.ММ.ГГГГ (например: 25.12.2026)\n"
        "• ДД.ММ.ГГ (например: 25.12.26)\n\n"
        "❌ /cancel - отменить"
    )


@router.message(HomeworkImportStates.waiting_for_manual_deadline)
async def process_manual_deadline(message: Message, state: FSMContext):
    """Получаем дедлайн и сохраняем задание без фото"""
    deadline_str = message.text.strip()

    date_formats = ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y"]
    deadline = None

    for fmt in date_formats:
        try:
            deadline = datetime.strptime(deadline_str, fmt)
            break
        except ValueError:
            continue

    if deadline is None:
        await message.answer(
            "❌ Неверный формат даты.\n\n"
            "Попробуй ещё раз (например: 25.12.2026):\n\n"
            "❌ /cancel - отменить"
        )
        return

    data = await state.get_data()
    temp_subject_id = data.get('temp_subject_id')
    temp_subject_name = data.get('temp_subject_name')
    temp_task_text = data.get('temp_task_text')

    new_homework = {
        'subject_id': temp_subject_id,
        'subject_name': temp_subject_name,
        'task_text': temp_task_text,
        'deadline': deadline,
        'photo_file_id': None  # фото нет
    }

    homeworks = data.get('homeworks', [])
    homeworks.append(new_homework)
    await state.update_data(homeworks=homeworks)

    await state.update_data(
        temp_subject_id=None,
        temp_subject_name=None,
        temp_task_text=None
    )

    response = f"✅ **Задание добавлено в список!**\n\n"
    response += f"📚 Предмет: {temp_subject_name}\n"
    response += f"📝 Задание: {temp_task_text}\n"
    response += f"📅 Дедлайн: {deadline.strftime('%d.%m.%Y')}\n"

    await message.answer(response)

    await state.set_state(HomeworkImportStates.waiting_for_next_action)
    await message.answer(
        f"📊 **В списке сейчас {len(homeworks)} заданий.**\n\n"
        "Что хочешь сделать?",
        reply_markup=get_next_action_keyboard()
    )


@router.callback_query(HomeworkImportStates.waiting_for_next_action, F.data == "homework_add_more")
async def add_more_homework(callback, state: FSMContext):
    """Добавляем ещё одно задание - показываем выбор способа"""
    await callback.message.edit_text(
        "📚 **Добавление нового задания**\n\n"
        "Выбери способ:",
        reply_markup=homework_keyboard
    )
    await callback.answer()


@router.callback_query(HomeworkImportStates.waiting_for_next_action, F.data == "homework_finish")
async def finish_and_save(callback, state: FSMContext):
    """Завершаем ввод и сохраняем все задания в БД"""
    data = await state.get_data()
    homeworks = data.get('homeworks', [])

    if not homeworks:
        await callback.message.edit_text("❌ Нет заданий для сохранения.")
        await state.clear()
        await callback.answer()
        return

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(callback.from_user.id)).first()
    close_db(db)


    saved_count = 0
    errors = []

    await callback.message.edit_text(f"💾 Сохраняю {len(homeworks)} заданий...")

    for i, hw in enumerate(homeworks, 1):
        task = create_task(
            subject_id=hw['subject_id'],
            title=hw['task_text'],
            deadline=hw['deadline'],
            created_by=user.id,
            photo_file_id=hw.get('photo_file_id')
        )

        if task is None:
            errors.append(f"Задание {i}: {hw['subject_name']}")
        else:
            saved_count += 1

    if errors:
        response = f"⚠️ **Сохранено частично:** {saved_count}/{len(homeworks)}\n\n"
        response += f"Ошибки:\n" + "\n".join(errors[:5])
    else:
        response = f"✅ **Все {saved_count} заданий успешно сохранены!**"

    await callback.message.edit_text(response)
    await state.clear()
    await callback.answer()


@router.message(Command("cancel"))
async def cancel_import(message: Message, state: FSMContext):
    """Отмена импорта"""
    await state.clear()
    await message.answer(
        "❌ Импорт домашнего задания отменён.",
        reply_markup=ReplyKeyboardRemove()
    )