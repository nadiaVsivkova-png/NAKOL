from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import get_db, close_db
from database.models import User, Subject
from database.group_functions import delete_subject

router = Router()


class RemoveSubjectStates(StatesGroup):
    waiting_for_subject_selection = State()
    waiting_for_confirmation = State()


def get_user_subjects(user_id: int, group_id: int = None):
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.role == "starosta" and group_id:
            subjects = db.query(Subject).filter(Subject.group_id == group_id).all()
        else:
            subjects = db.query(Subject).filter(Subject.user_id == user_id).all()
        return subjects
    finally:
        close_db(db)


def get_subjects_keyboard(subjects):
    """Создает инлайн-клавиатуру со списком предметов"""
    buttons = []
    for i, subject in enumerate(subjects, 1):
        buttons.append([InlineKeyboardButton(
            text=f"{i}. {subject.name}",
            callback_data=f"remove_subject_{subject.id}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="remove_subject_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirmation_keyboard(subject_id: int, subject_name: str):
    """Создает клавиатуру для подтверждения удаления"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"remove_confirm_{subject_id}")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data="remove_subject_cancel")]
    ])


@router.message(Command("remove_subject"))
async def cmd_remove_subject(message: Message, state: FSMContext):
    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()
    close_db(db)

    subjects = get_user_subjects(user.id, user.group_id)

    if not subjects:
        await message.answer(
            "❌ У вас нет предметов для удаления.\n\n"
        )
        return

    subjects_data = [{'id': s.id, 'name': s.name} for s in subjects]
    await state.update_data(subjects=subjects_data)
    await state.set_state(RemoveSubjectStates.waiting_for_subject_selection)

    subjects_text = "📋 Список ваших предметов:\n\n"
    for i, subject in enumerate(subjects, 1):
        subjects_text += f"{i}. {subject.name}\n"
    subjects_text += "\n👇 Выберите предмет, который хотите удалить:"

    await message.answer(
        subjects_text,
        reply_markup=get_subjects_keyboard(subjects),
        parse_mode="Markdown"
    )


@router.callback_query(RemoveSubjectStates.waiting_for_subject_selection, F.data.startswith("remove_subject_"))
async def process_subject_selection(callback: CallbackQuery, state: FSMContext):
    callback_data = callback.data

    if callback_data == "remove_subject_cancel":
        await callback.message.edit_text("❌ Удаление предмета отменено.")
        await callback.answer()
        await state.clear()
        return

    subject_id = int(callback_data.replace("remove_subject_", ""))

    data = await state.get_data()
    subjects = data.get('subjects', [])

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

    await state.update_data(subject_id=subject_id, subject_name=subject_name)
    await state.set_state(RemoveSubjectStates.waiting_for_confirmation)

    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить предмет «{subject_name}»?\n\n"
        f"❗️ Внимание: Вместе с предметом будут удалены все будущие задания.\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=get_confirmation_keyboard(subject_id, subject_name),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(RemoveSubjectStates.waiting_for_confirmation, F.data.startswith("remove_confirm_"))
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    subject_id = int(callback.data.replace("remove_confirm_", ""))

    data = await state.get_data()
    subject_name = data.get('subject_name')
    user_telegram_id = callback.from_user.id

    db = get_db()
    user = db.query(User).filter(User.telegram_id == str(user_telegram_id)).first()
    close_db(db)

    if not user:
        await callback.message.edit_text("❌ Пользователь не найден.")
        await callback.answer()
        await state.clear()
        return

    await callback.message.edit_text(f"🔄 Удаляю предмет «{subject_name}» и будущие задания...")

    if user.role == "starosta" and user.group_id:
        deleted_count = delete_subject(subject_id=subject_id, group_id=user.group_id)
    else:
        deleted_count = delete_subject(subject_id=subject_id, user_id=user.id)

    if deleted_count is None:
        await callback.message.edit_text(
            f"❌ Ошибка: Предмет «{subject_name}» не найден или нет прав на удаление."
        )
    else:
        if deleted_count == 0:
            tasks_message = "Не было будущих заданий"
        else:
            tasks_message = f"удалено будущих заданий: {deleted_count}"
        await callback.message.edit_text(
            f"✅ Предмет «{subject_name}» успешно удалён!\n\n📊 {tasks_message}."
        )

    await callback.answer()
    await state.clear()


@router.callback_query(RemoveSubjectStates.waiting_for_confirmation, F.data == "remove_subject_cancel")
async def process_cancel_confirmation(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Удаление предмета отменено.")
    await callback.answer()
    await state.clear()
