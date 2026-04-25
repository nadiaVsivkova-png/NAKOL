from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, \
    InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import get_db, close_db
from database.models import User, Subject, Group, Task
from database.group_functions import create_task, get_or_create_subject
from datetime import datetime
import asyncio

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
    close_db(db)

    if user.is_elder and user.group_id:
        subject_id = get_or_create_subject(subject_name, group_id=user.group_id)
    else:
        subject_id = get_or_create_subject(subject_name, user_id=user.id)

    if subject_id is None:
        await message.answer(
            f"❌ Не удалось создать или найти предмет «{subject_name}».\n\n"
            f"Попробуй другое название:"
        )
        return

    await state.update_data(temp_subject_id=subject_id, temp_subject_name=subject_name)
    await state.set_state(HomeworkImportStates.waiting_for_photo_deadline)

    await message.answer(
        f"✅ Предмет: {subject_name}\n\n"
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
    close_db(db)

    if user.is_elder and user.group_id:
        subject_id = get_or_create_subject(subject_name, group_id=user.group_id)
    else:
        subject_id = get_or_create_subject(subject_name, user_id=user.id)

    if subject_id is None:
        await message.answer(
            f"❌ Не удалось создать или найти предмет «{subject_name}».\n\n"
            f"Попробуй другое название:"
        )
        return

    await state.update_data(temp_subject_id=subject_id, temp_subject_name=subject_name)
    await state.set_state(HomeworkImportStates.waiting_for_task_text)

    await message.answer(
        f"✅ Предмет: {subject_name}\n\n"
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

    saved_tasks = []
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
            saved_tasks.append(task)

    close_db(db)

    if errors:
        response = f"⚠️ **Сохранено частично:** {saved_count}/{len(homeworks)}\n\n"
        response += f"Ошибки:\n" + "\n".join(errors[:5])
        await callback.message.edit_text(response)
        await state.clear()
        await callback.answer()
        return

    # Сохраняем ID заданий в состояние для последующей отправки
    task_ids = [t.id for t in saved_tasks]
    await state.update_data(saved_task_ids=task_ids)

    # Просто выводим сообщение без кнопки
    await callback.message.edit_text(
        f"✅ **{saved_count} заданий успешно сохранены!**\n\n"
        f"📊 Сохранено: {saved_count}\n\n"
        f"📢 Чтобы отправить задания в группу, напиши в чат команду:\n"
        f"`/send_to_group`\n\n"
        f"Ты можешь отправить их сейчас или позже.",
        parse_mode="Markdown"
    )

    await callback.answer()


async def send_single_task_to_group(task_id: int, group_telegram_id: int, bot: Bot):
    """
    Отправляет одно задание в группу по его ID.

    Args:
        task_id: ID задания в БД
        group_telegram_id: Telegram ID группы (куда отправлять)

    Returns:
        bool: True если успешно, False если ошибка
    """
    db = get_db()

    # Получаем задание из БД
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        close_db(db)
        return False

    # Получаем предмет (чтобы вывести название)
    subject = db.query(Subject).filter(Subject.id == task.subject_id).first()
    subject_name = subject.name if subject else "Неизвестный предмет"
    close_db(db)

    # Форматируем дату
    deadline_str = task.deadline.strftime("%d.%m.%Y")

    # Текст сообщения
    message_text = (
        f"📚 **Новое задание в группе!**\n\n"
        f"📖 Предмет: {subject_name}\n"
        f"📝 Задание: {task.title}\n"
        f"📅 Дедлайн: {deadline_str}\n"
    )

    # Кнопка для просмотра фото (если есть)
    keyboard = None
    if task.photo_file_id:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📸 Показать фото", callback_data=f"show_photo:{task.id}")]
        ])

    # Отправляем в группу
    try:
        if task.photo_file_id:
            await bot.send_photo(
                chat_id=group_telegram_id,
                photo=task.photo_file_id,
                caption=message_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await bot.send_message(
                chat_id=group_telegram_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        return True
    except Exception as e:
        print(f"Ошибка отправки задания {task_id} в группу: {e}")
        return False


@router.message(Command("send_to_group"))
async def send_to_group_command(message: Message, state: FSMContext):
    """Отправляет задания в группу по команде"""
    data = await state.get_data()
    task_ids = data.get('saved_task_ids', [])

    if not task_ids:
        await message.answer(
            "❌ Нет заданий для отправки.\n\n"
            "Сначала добавь задания через /import_homework"
        )
        return

    # Получаем пользователя и его группу
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()

    if not user or not user.group_id:
        await message.answer(
            "❌ У тебя нет группы для отправки."
        )
        close_db(db)
        return

    group_id = user.group_id
    group = db.query(Group).filter(Group.id == group_id).first()
    group_telegram_id = group.telegram_id if group else None

    close_db(db)

    if not group_telegram_id:
        await message.answer("❌ Группа не найдена")
        return

    await message.answer(f"📤 Отправляю {len(task_ids)} заданий в группу...")

    sent_count = 0
    for task_id in task_ids:
        success = await send_single_task_to_group(task_id, group_telegram_id, message.bot)
        if success:
            sent_count += 1
        await asyncio.sleep(0.5)

    await message.answer(
        f"✅ **Отправлено в группу:** {sent_count}/{len(task_ids)}\n\n"
        f"Студенты группы получили уведомления."
    )

    # Очищаем ID заданий после отправки
    await state.update_data(saved_task_ids=[])


@router.callback_query(F.data.startswith("show_photo:"))
async def show_photo(callback: CallbackQuery):
    """Отправляет фото задания при нажатии на кнопку"""
    task_id = int(callback.data.split(":")[1])

    db = get_db()
    task = db.query(Task).filter(Task.id == task_id).first()
    close_db(db)

    if not task or not task.photo_file_id:
        await callback.answer("❌ Фото не найдено", show_alert=True)
        return

    await callback.message.answer_photo(
        photo=task.photo_file_id,
        caption=f"📸 Фото к заданию «{task.title}»"
    )
    await callback.answer()
