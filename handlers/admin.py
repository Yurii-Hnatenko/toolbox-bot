from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, delete
from database import async_session
from models import User, Toolbox, ToolCheck, BoxStatus
from config import ADMIN_IDS
from handlers.common import force_user_menu_update

router = Router()

class AdminState(StatesGroup):
    adding_toolbox = State()
    setting_role_user_id = State()
    setting_role = State()

@router.message(F.text == "👥 Керування ролями")
async def manage_roles(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ заборонено")
        return
    await state.set_state(AdminState.setting_role_user_id)
    await message.answer("Надішліть Telegram ID користувача для керування ролями:")

@router.message(AdminState.setting_role_user_id)
async def get_user_for_role(message: Message, state: FSMContext):
    try:
        telegram_id = int(message.text)
        async with async_session() as session:
            user = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = user.scalar_one_or_none()
            if not user:
                await message.answer("❌ Користувача не знайдено. Спочатку він має запустити бота (/start)")
                await state.clear()
                return
            
            await state.update_data(target_user_id=user.id)
            
            user_roles = user.role_list
            
            buttons = []
            for role in ["operator", "mechanic", "admin"]:
                if role in user_roles:
                    buttons.append([InlineKeyboardButton(text=f"✅ {role} (видалити)", callback_data=f"remove_role_{role}")])
                else:
                    buttons.append([InlineKeyboardButton(text=f"➕ {role} (додати)", callback_data=f"add_role_{role}")])
            
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await message.answer(
                f"👤 {user.full_name}\nПоточні ролі: {', '.join(user_roles) if user_roles else 'немає'}\n\n"
                f"Оберіть дію:",
                reply_markup=kb
            )
            await state.set_state(AdminState.setting_role)
    except ValueError:
        await message.answer("❌ Невірний ID. Надішліть число.")

@router.callback_query(F.data.startswith("add_role_"))
async def add_user_role(callback: CallbackQuery, state: FSMContext):
    role_name = callback.data.split("_")[2]
    data = await state.get_data()
    user_id = data.get("target_user_id")
    
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user and not user.has_role(role_name):
            user.add_role(role_name)
            await session.commit()
            
            # Оновлюємо меню користувача
            await force_user_menu_update(user.telegram_id, callback.bot)
            
            user_roles = user.role_list
            buttons = []
            for role in ["operator", "mechanic", "admin"]:
                if role in user_roles:
                    buttons.append([InlineKeyboardButton(text=f"✅ {role} (видалити)", callback_data=f"remove_role_{role}")])
                else:
                    buttons.append([InlineKeyboardButton(text=f"➕ {role} (додати)", callback_data=f"add_role_{role}")])
            
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await callback.message.edit_text(
                f"👤 {user.full_name}\nПоточні ролі: {', '.join(user_roles)}\n\n"
                f"✅ Додано роль '{role_name}'\nОберіть дію:",
                reply_markup=kb
            )
        else:
            await callback.answer(f"⚠️ Роль '{role_name}' вже є у користувача")
    await callback.answer()

@router.callback_query(F.data.startswith("remove_role_"))
async def remove_user_role(callback: CallbackQuery, state: FSMContext):
    role_name = callback.data.split("_")[2]
    data = await state.get_data()
    user_id = data.get("target_user_id")
    
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user and user.has_role(role_name):
            if len(user.role_list) <= 1:
                await callback.answer("❌ Не можна видалити останню роль у користувача", show_alert=True)
                return
            user.remove_role(role_name)
            await session.commit()
            
            # Оновлюємо меню користувача
            await force_user_menu_update(user.telegram_id, callback.bot)
            
            user_roles = user.role_list
            buttons = []
            for role in ["operator", "mechanic", "admin"]:
                if role in user_roles:
                    buttons.append([InlineKeyboardButton(text=f"✅ {role} (видалити)", callback_data=f"remove_role_{role}")])
                else:
                    buttons.append([InlineKeyboardButton(text=f"➕ {role} (додати)", callback_data=f"add_role_{role}")])
            
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await callback.message.edit_text(
                f"👤 {user.full_name}\nПоточні ролі: {', '.join(user_roles)}\n\n"
                f"🗑️ Видалено роль '{role_name}'\nОберіть дію:",
                reply_markup=kb
            )
        else:
            await callback.answer(f"⚠️ У користувача немає ролі '{role_name}'")
    await callback.answer()

# Решта функцій (manage_boxes, add_toolbox, delete_toolbox, global_stats) залишаються без змін