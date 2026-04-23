from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'database'))
from db import get_db
from models import User, Group, GroupMember

router = Router()

# состояния для FSM
class UrgentState(StatesGroup):
    waiting_for_text = State()


@router.message(Command("urgent"))
async def cmd_urgent(message: Message, state: FSMContext):
    user_id = message.from_user.id
    db = get_db()
    
    try:
        # проверяем, что пользователь - староста
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await message.answer("❌ Ты не зарегистрирован")
            return
        
        if user.role != "starosta":
            await message.answer("❌ Только староста может отправлять срочные уведомления")
            return
        
        # находим группу старосты
        group = db.query(Group).filter(Group.starosta_id == user_id).first()
        if not group:
            await message.answer("❌ У тебя нет группы")
            return
        
        # находим всех участников группы
        members = db.query(User, GroupMember).join(
            GroupMember, User.id == GroupMember.user_id
        ).filter(
            GroupMember.group_id == group.id
        ).all()
        
        if not members:
            await message.answer("❌ В группе нет участников")
            return
        
        # сохраняем данные в состояние
        await state.update_data(
            group_id=group.id,
            members=[m.telegram_id for m, _ in members]
        )
        await state.set_state(UrgentState.waiting_for_text)
        
        await message.answer("📝 Напиши текст срочного уведомления:")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        db.close()


@router.message(UrgentState.waiting_for_text)
async def process_urgent_text(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    members = data.get("members", [])
    group_id = data.get("group_id")
    user_id = message.from_user.id
    
    db = get_db()
    
    try:
        sent_count = 0
        for member_id in members:
            try:
                await message.bot.send_message(
                    member_id,
                    f"🚨 СРОЧНО от старосты:\n\n{text}"
                )
                sent_count += 1
            except Exception as e:
                print(f"Не удалось отправить {member_id}: {e}")
        
        await message.answer(f"✅ Уведомление отправлено {sent_count} участникам")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке: {e}")
    finally:
        db.close()
        await state.clear()