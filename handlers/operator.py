from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, desc
from database import async_session
from models import User, Toolbox, ToolCheck, BoxStatus
from keyboards import toolboxes_list_kb, main_menu_by_role
from handlers.common import active_role
from datetime import datetime
import os

router = Router()

class CheckState(StatesGroup):
    selecting_toolbox = State()
    selecting_tool = State()
    comment = State()
    photo = State()

@router.message(F.text == "📋 Перевірити ящик")
async def select_toolbox(message: Message, state: FSMContext):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        if not toolboxes:
            await message.answer("❌ Немає створених ящиків.")
            return
        await state.set_state(CheckState.selecting_toolbox)
        await message.answer("Оберіть ящик:", reply_markup=toolboxes_list_kb(toolboxes, "check"))

@router.message(F.text == "📜 Історія моїх перевірок")
async def my_history(message: Message):
    async with async_session() as session:
        user = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user.scalar_one()
        checks = await session.execute(
            select(ToolCheck).where(ToolCheck.user_id == user.id)
            .order_by(desc(ToolCheck.timestamp)).limit(20)
        )
        checks = checks.scalars().all()
        if not checks:
            await message.answer("📭 У вас ще немає перевірок.")
            return
        text = "📜 Історія ваших перевірок:\n\n"
        for ch in checks:
            toolbox = await session.get(Toolbox, ch.toolbox_id)
            text += f"📦 {toolbox.name}\n   🔧 {ch.tool_name}: {'✅' if ch.is_present else '❌'}\n   🕐 {ch.timestamp.strftime('%d.%m.%Y %H:%M:%S')}\n"
            if ch.comment:
                text += f"   📝 {ch.comment}\n"
            text += "   ---\n\n"
        await message.answer(text)

@router.message(F.text == "📸 Фото інструментів")
async def view_tool_photos(message: Message):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        if not toolboxes:
            await message.answer("❌ Немає створених ящиків.")
            return
        await message.answer("Оберіть ящик:", reply_markup=toolboxes_list_kb(toolboxes, "photos"))
