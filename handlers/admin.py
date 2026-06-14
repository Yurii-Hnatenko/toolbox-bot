from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, delete
from database import async_session
from models import User, Toolbox, ToolCheck, BoxStatus
from config import ADMIN_IDS
from handlers.common import active_role
from keyboards import main_menu_by_role, toolboxes_list_kb

router = Router()

class AdminState(StatesGroup):
    adding_toolbox = State()
    setting_role_user_id = State()
    setting_role = State()

@router.message(F.text == "👥 Керування ролями")
async def manage_roles(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ заборонено.")
        return
    await state.set_state(AdminState.setting_role_user_id)
    await message.answer("Введіть Telegram ID користувача:")

@router.message(AdminState.setting_role_user_id)
async def get_user_for_role(message: Message, state: FSMContext):
    try:
        telegram_id = int(message.text)
        async with async_session() as session:
            user = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = user.scalar_one_or_none()
            if not user:
                await message.answer("❌ Користувача не знайдено.")
                return
            await state.update_data(target_user_id=user.id)
            buttons = [[InlineKeyboardButton(text=f"➕ {r}", callback_data=f"add_role_{r}") if not user.has_role(r) else InlineKeyboardButton(text=f"✅ {r} (видалити)", callback_data=f"remove_role_{r}") for r in ["operator", "mechanic", "admin"]]]
            await message.answer(f"👤 {user.full_name}\nРолі: {', '.join(user.role_list)}\nОберіть дію:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
            await state.set_state(AdminState.setting_role)
    except ValueError:
        await message.answer("❌ Невірний ID. Введіть число.")

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
            await callback.message.answer(f"✅ Додано роль '{role_name}' для {user.full_name}.")
        else:
            await callback.answer("⚠️ Роль вже є.")
    await callback.answer
