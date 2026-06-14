from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session
from models import User
from keyboards import main_menu_by_role
from sqlalchemy import select
from handlers.common import active_role

router = Router()

@router.message(F.text == "🔄 Перемкнути роль")
async def switch_role_menu(message: Message):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one()
        roles = user.role_list
        if len(roles) <= 1:
            await message.answer("❌ У вас лише одна роль.")
            return
        buttons = [[InlineKeyboardButton(text=f"✅ {r.capitalize()}" if r == active_role.get(message.from_user.id) else f"🔄 {r.capitalize()}", callback_data=f"switch_role_{r}")] for r in roles]
        await message.answer("Оберіть роль:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("switch_role_"))
async def set_active_role(callback: CallbackQuery):
    new_role = callback.data.split("_")[2]
    active_role[callback.from_user.id] = new_role
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = result.scalar_one()
        await callback.message.answer(f"✅ Активну роль змінено на: {new_role.capitalize()}", reply_markup=main_menu_by_role(new_role))
        await callback.message.delete()
    await callback.answer()
