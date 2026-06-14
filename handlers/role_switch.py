from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session
from models import User
from keyboards import main_menu_by_role
from sqlalchemy import select
from handlers.common import active_role
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "🔄 Перемкнути роль")
async def switch_role_menu(message: Message):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Користувача не знайдено. Надішліть /start")
            return
        
        roles = user.role_list
        
        if len(roles) <= 1:
            await message.answer("❌ У вас лише одна роль. Немає куди перемикатись.")
            return
        
        current_role = active_role.get(message.from_user.id, user.primary_role)
        
        buttons = []
        for role in roles:
            if role == current_role:
                buttons.append([InlineKeyboardButton(text=f"✅ {role.capitalize()} (активна)", callback_data=f"switch_role_{role}")])
            else:
                buttons.append([InlineKeyboardButton(text=f"🔄 {role.capitalize()}", callback_data=f"switch_role_{role}")])
        
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(
            f"📋 Ваші ролі: {', '.join(roles)}\n"
            f"👉 Поточна активна роль: {current_role.capitalize()}\n\n"
            f"Оберіть нову роль:",
            reply_markup=kb
        )

@router.callback_query(F.data.startswith("switch_role_"))
async def set_active_role(callback: CallbackQuery):
    new_role = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Користувача не знайдено")
            return
        
        if new_role not in user.role_list:
            await callback.answer(f"❌ У вас немає ролі {new_role.capitalize()}")
            return
        
        active_role[user_id] = new_role
        logger.info(f"Користувач {user_id} переключив роль на {new_role}")
        
        await callback.message.answer(
            f"✅ Активну роль змінено на: *{new_role.capitalize()}*\n\n"
            f"Ваше меню оновлено:",
            reply_markup=main_menu_by_role(new_role),
            parse_mode="Markdown"
        )
        
        try:
            await callback.message.delete()
        except Exception:
            pass
        
    await callback.answer()
