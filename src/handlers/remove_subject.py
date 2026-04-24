from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import get_db, close_db
from database.models import User, Subject
from database.group_functions import delete_subject  # функция Кати

router = Router()


# Состояния для FSM
class RemoveSubjectStates(StatesGroup):
    waiting_for_subject_selection = State()  # ожидаем выбора предмета
    waiting_for_confirmation = State()  # ожидаем подтверждения


# Функция для получения списка предметов пользователя
def get_user_subjects(user_id: int, group_id: int = None):
    """
    Возвращает список предметов для пользователя.
    Если есть group_id и пользователь староста - предметы группы.
    Иначе - личные предметы.
    """
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()

        if user and user.is_elder and group_id:
            # Староста - предметы группы
            subjects = db.query(Subject).filter(Subject.group_id == group_id).all()
        else:
            # Обычный пользователь - личные предметы
            subjects = db.query(Subject).filter(Subject.user_id == user_id).all()

        return subjects
    finally:
        close_db(db)


# Функция для создания клавиатуры с нумерованным списком
def get_subjects_keyboard(subjects):
    """Создает инлайн-клавиатуру со списком предметов"""
    keyboard = InlineKeyboardMarkup(row_width=1)

    for i, subject in enumerate(subjects, 1):
        keyboard.add(
            InlineKeyboardButton(
                text=f"{i}. {subject.name}",
                callback_data=f"remove_subject_{subject.id}"
            )
        )

    # Кнопка отмены
    keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="remove_subject_cancel"))

    return keyboard


# Функция для создания клавиатуры подтверждения
def get_confirmation_keyboard(subject_id: int, subject_name: str):
    """Создает клавиатуру для подтверждения удаления"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"remove_confirm_{subject_id}"),
        InlineKeyboardButton(text="❌ Нет, отмена", callback_data="remove_subject_cancel")
    )
    return keyboard


@router.message(Command("remove_subject"))
async def cmd_remove_subject(message: Message, state: FSMContext):
    """Показывает список предметов для удаления"""

    # Получаем пользователя из БД
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    # Получаем список предметов
    subjects = get_user_subjects(user.id, user.group_id)

    if not subjects:
        await message.answer(
            "❌ У вас нет предметов для удаления.\n\n"
            "Сначала добавьте предметы через /add_subject"
        )
        return

    # Сохраняем список предметов в состояние
    subjects_data = [{'id': s.id, 'name': s.name} for s in subjects]
    await state.update_data(subjects=subjects_data)
    await state.set_state(RemoveSubjectStates.waiting_for_subject_selection)

    # Формируем нумерованный список
    subjects_text = "📋 **Список ваших предметов:**\n\n"
    for i, subject in enumerate(subjects, 1):
        subjects_text += f"{i}. {subject.name}\n"

    subjects_text += "\n👇 **Выберите предмет, который хотите удалить:**"

    await message.answer(
        subjects_text,
        reply_markup=get_subjects_keyboard(subjects),
        parse_mode="Markdown"
    )


@router.callback_query(RemoveSubjectStates.waiting_for_subject_selection, F.data.startswith("remove_subject_"))
async def process_subject_selection(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор предмета для удаления"""

    callback_data = callback.data

    if callback_data == "remove_subject_cancel":
        await callback.message.edit_text("❌ Удаление предмета отменено.")
        await callback.answer()
        await state.clear()
        return

    # Извлекаем ID предмета
    subject_id = int(callback_data.replace("remove_subject_", ""))

    # Получаем список предметов из состояния
    data = await state.get_data()
    subjects = data.get('subjects', [])

    # Находим название предмета
    subject_name = None
    for subject in subjects:
        if subject['id'] == subject_id:
            subject_name = subject['name']
            break

    if not subject_name:
        await callback.message.edit_text("❌ Предмет не найден. Попробуйте снова /remove_subject")
        await callback.answer()
        await state.clear()
        return

    # Сохраняем ID предмета в состояние
    await state.update_data(subject_id=subject_id, subject_name=subject_name)
    await state.set_state(RemoveSubjectStates.waiting_for_confirmation)

    # Показываем подтверждение
    await callback.message.edit_text(
        f"⚠️ **Вы уверены, что хотите удалить предмет «{subject_name}»?**\n\n"
        f"❗️ **Внимание:** Вместе с предметом будут удалены все **будущие** задания (срок сдачи которых ещё не наступил).\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=get_confirmation_keyboard(subject_id, subject_name),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(RemoveSubjectStates.waiting_for_confirmation, F.data.startswith("remove_confirm_"))
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    """Подтверждение удаления предмета"""

    # Извлекаем ID предмета
    subject_id = int(callback.data.replace("remove_confirm_", ""))

    # Получаем данные из состояния
    data = await state.get_data()
    subject_name = data.get('subject_name')
    user_telegram_id = callback.from_user.id

    # Получаем user_id и group_id из БД
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(user_telegram_id)).first()
    close_db(db)

    if not user:
        await callback.message.edit_text("❌ Пользователь не найден в базе данных.")
        await callback.answer()
        await state.clear()
        return

    # Отправляем сообщение о начале удаления
    await callback.message.edit_text(
        f"🔄 Удаляю предмет «{subject_name}» и связанные с ним будущие задания..."
    )

    # ВЫЗЫВАЕМ ФУНКЦИЮ delete_subject
    if user.is_elder and user.group_id:
        # Староста удаляет предмет из группы
        deleted_count = delete_subject(
            subject_id=subject_id,
            group_id=user.group_id
        )
    else:
        # Обычный пользователь удаляет свой личный предмет
        deleted_count = delete_subject(
            subject_id=subject_id,
            user_id=user.id
        )

    # Анализируем результат
    if deleted_count is None:
        await callback.message.edit_text(
            f"❌ Ошибка: Предмет «{subject_name}» не найден или у вас нет прав на его удаление.\n\n"
            f"Убедитесь, что предмет принадлежит вам, и попробуйте снова."
        )
    else:
        if deleted_count == 0:
            tasks_message = "не было будущих заданий"
        else:
            tasks_message = f"удалено будущих заданий: {deleted_count}"

        await callback.message.edit_text(
            f"✅ **Предмет «{subject_name}» успешно удалён!**\n\n"
            f"📊 {tasks_message}."
        )

    await callback.answer()
    await state.clear()


@router.callback_query(RemoveSubjectStates.waiting_for_confirmation, F.data == "remove_subject_cancel")
async def process_cancel_confirmation(callback: CallbackQuery, state: FSMContext):
    """Отмена удаления"""
    await callback.message.edit_text("❌ Удаление предмета отменено.")
    await callback.answer()
    await state.clear()