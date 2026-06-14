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
    
    active_role[user_id] = new_role
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one()
        
        await callback.message.edit_text(
            f"✅ Активну роль змінено на: *{new_role.capitalize()}*\n\n"
            f"Ваше меню оновлено. Натисніть кнопку нижче:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Показати меню", callback_data="show_menu")]
            ]),
            parse_mode="Markdown"
        )
        
    await callback.answer()

@router.callback_query(F.data == "show_menu")
async def show_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    current_role = active_role.get(user_id, "operator")
    
    await callback.message.edit_text(
        f"🔧 Ваше меню (роль: {current_role.capitalize()})",
        reply_markup=main_menu_by_role(current_role)
    )
    await callback.answer()
