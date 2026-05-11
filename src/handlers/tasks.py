from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from datetime import datetime, timedelta
import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'database'))
from db import get_db
from models import User, Task, UserTask, Subject, Meme

router = Router()


def get_random_meme(db):
    """возвращает случайный мем из базы или None"""
    memes = db.query(Meme).all()
    if memes:
        return random.choice(memes)
    return None


@router.message(Command("list"))
async def cmd_list(message: Message):
    user_id = message.from_user.id
    db = get_db()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await message.answer("❌ Ты не зарегистрирован. Введи /start")
            return
        
        user_tasks = db.query(UserTask, Task, Subject).join(
            Task, UserTask.task_id == Task.id
        ).join(
            Subject, Task.subject_id == Subject.id
        ).filter(
            UserTask.user_id == user.id,
            UserTask.status == "active"
        ).all()
        
        if not user_tasks:
            await message.answer("🎉 У тебя нет активных заданий!")
            return
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        end_of_week = today + timedelta(days=(7 - today.weekday()))
        
        urgent = []
        this_week = []
        other = []
        
        for user_task, task, subject in user_tasks:
            task_info = {
                "id": task.id,
                "subject": subject.name,
                "title": task.title,
                "deadline": task.deadline,
                "has_photo": hasattr(task, 'photo_file_id') and task.photo_file_id is not None
            }
            
            if task.deadline <= tomorrow:
                urgent.append(task_info)
            elif task.deadline <= end_of_week:
                this_week.append(task_info)
            else:
                other.append(task_info)
        
        response = "📋 <b>Твои задания:</b>\n\n"
        
        if urgent:
            response += "🔴 <b>СРОЧНЫЕ (до завтра):</b>\n"
            for t in urgent:
                photo_icon = " 📎" if t["has_photo"] else ""
                response += f"  ID {t['id']}: {t['subject']} – {t['title']} (до {t['deadline'].strftime('%d.%m')}){photo_icon}\n"
            response += "\n"
        
        if this_week:
            response += "🟡 <b>НА ЭТОЙ НЕДЕЛЕ:</b>\n"
            for t in this_week:
                photo_icon = " 📎" if t["has_photo"] else ""
                response += f"  ID {t['id']}: {t['subject']} – {t['title']} (до {t['deadline'].strftime('%d.%m')}){photo_icon}\n"
            response += "\n"
        
        if other:
            response += "🟢 <b>ОСТАЛЬНЫЕ:</b>\n"
            for t in other:
                photo_icon = " 📎" if t["has_photo"] else ""
                response += f"  ID {t['id']}: {t['subject']} – {t['title']} (до {t['deadline'].strftime('%d.%m')}){photo_icon}\n"
        
        response += "\n✏️ Чтобы отметить задание выполненным, введи /done"
        
        await message.answer(response, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        db.close()


@router.message(Command("free_time"))
async def cmd_free_time(message: Message):
    user_id = message.from_user.id
    db = get_db()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await message.answer("❌ Ты не зарегистрирован. Введи /start")
            return
        
        user_tasks = db.query(UserTask, Task, Subject).join(
            Task, UserTask.task_id == Task.id
        ).join(
            Subject, Task.subject_id == Subject.id
        ).filter(
            UserTask.user_id == user.id,
            UserTask.status == "active"
        ).order_by(Task.deadline.asc()).limit(2).all()
        
        if not user_tasks:
            await message.answer("🎉 Ура! Все задания выполнены. Отдохни :)")
            return
        
        response = "⏳ У тебя есть время? Займись вот этим:\n\n"
        for user_task, task, subject in user_tasks:
            response += f"• {subject.name} – {task.title} (дедлайн {task.deadline.strftime('%d.%m')})\n"
        
        await message.answer(response)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        db.close()


@router.message(Command("done"))
async def cmd_done(message: Message):
    user_id = message.from_user.id
    db = get_db()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await message.answer("❌ Ты не зарегистрирован")
            return
        
        user_tasks = db.query(UserTask, Task, Subject).join(
            Task, UserTask.task_id == Task.id
        ).join(
            Subject, Task.subject_id == Subject.id
        ).filter(
            UserTask.user_id == user.id,
            UserTask.status == "active"
        ).all()
        
        if not user_tasks:
            await message.answer("🎉 У тебя нет активных заданий!")
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for user_task, task, subject in user_tasks:
            button_text = f"{subject.name} – {task.title} (до {task.deadline.strftime('%d.%m')})"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"done_{task.id}"
                )
            ])
        
        await message.answer("✅ Выбери задание, которое выполнил:", reply_markup=keyboard)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        db.close()


@router.callback_query(F.data.startswith("done_"))
async def process_done_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    task_id = int(callback.data.split("_")[1])
    db = get_db()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await callback.answer("❌ Ты не зарегистрирован")
            return
        
        user_task = db.query(UserTask).filter(
            UserTask.user_id == user.id,
            UserTask.task_id == task_id,
            UserTask.status == "active"
        ).first()
        
        if not user_task:
            await callback.answer("❌ Задание не найдено или уже выполнено")
            return
        
        task = db.query(Task).filter(Task.id == task_id).first()
        subject = db.query(Subject).filter(Subject.id == task.subject_id).first()
        
        user_task.status = "done"
        user_task.completed_at = datetime.now()
        db.commit()
        
        meme = get_random_meme(db)
        
        await callback.message.edit_reply_markup(reply_markup=None)
        
        if meme:
            if meme.type == "text":
                await callback.message.answer(
                    f"✅ Задание <b>{subject.name} – {task.title}</b> выполнено!\n\n{meme.content}",
                    parse_mode="HTML"
                )
            elif meme.type == "photo":
                await callback.message.answer_photo(
                    meme.content,
                    caption=f"✅ Задание <b>{subject.name} – {task.title}</b> выполнено!",
                    parse_mode="HTML"
                )
        else:
            await callback.message.answer(
                f"✅ Задание <b>{subject.name} – {task.title}</b> выполнено! Ты справился!",
                parse_mode="HTML"
            )
        
        await callback.answer("Готово!")
        
    except Exception as e:
        await callback.answer(f"Ошибка: {e}")
        db.rollback()
    finally:
        db.close()