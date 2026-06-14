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
            
            buttons = []
            for role in ["operator", "mechanic", "admin"]:
                if user.has_role(role):
                    buttons.append([InlineKeyboardButton(text=f"✅ {role} (видалити)", callback_data=f"remove_role_{role}")])
                else:
                    buttons.append([InlineKeyboardButton(text=f"➕ {role} (додати)", callback_data=f"add_role_{role}")])
            
            await message.answer(
                f"👤 {user.full_name}\nПоточні ролі: {', '.join(user.role_list)}\nОберіть дію:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
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
    await callback.answer()
    await get_user_for_role(callback.message, state)

@router.callback_query(F.data.startswith("remove_role_"))
async def remove_user_role(callback: CallbackQuery, state: FSMContext):
    role_name = callback.data.split("_")[2]
    data = await state.get_data()
    user_id = data.get("target_user_id")
    
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user and user.has_role(role_name):
            if len(user.role_list) <= 1:
                await callback.answer("❌ Не можна видалити останню роль.", show_alert=True)
                return
            user.remove_role(role_name)
            await session.commit()
            await callback.message.answer(f"🗑️ Видалено роль '{role_name}' у {user.full_name}.")
        else:
            await callback.answer("⚠️ Ролі немає.")
    await callback.answer()
    await get_user_for_role(callback.message, state)

@router.message(F.text == "📦 Керування ящиками")
async def manage_boxes(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ заборонено.")
        return
    
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        
        if toolboxes:
            await message.answer("Список ящиків:", reply_markup=toolboxes_list_kb(toolboxes, "adminbox"))
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Додати ящик", callback_data="add_toolbox")],
            [InlineKeyboardButton(text="❌ Видалити ящик", callback_data="delete_toolbox")]
        ])
        await message.answer("Керування:", reply_markup=kb)

@router.callback_query(F.data == "add_toolbox")
async def add_toolbox(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.adding_toolbox)
    await callback.message.answer("Введіть назву нового ящика (до 15 шт.):")
    await callback.answer()

@router.message(AdminState.adding_toolbox)
async def save_new_toolbox(message: Message, state: FSMContext):
    name = message.text.strip()
    
    async with async_session() as session:
        count = await session.execute(select(Toolbox))
        if len(count.scalars().all()) >= 15:
            await message.answer("❌ Досягнуто ліміт (15 ящиків).")
            return
        
        existing = await session.execute(select(Toolbox).where(Toolbox.name == name))
        if existing.scalar_one_or_none():
            await message.answer("❌ Ящик з такою назвою вже існує.")
        else:
            new_box = Toolbox(name=name)
            new_box.set_tools([])
            session.add(new_box)
            await session.commit()
            await message.answer(f"✅ Ящик '{name}' створено.")
    await state.clear()

@router.callback_query(F.data == "delete_toolbox")
async def delete_toolbox_menu(callback: CallbackQuery):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        
        if not toolboxes:
            await callback.message.answer("❌ Немає ящиків.")
            await callback.answer()
            return
        
        buttons = [[InlineKeyboardButton(text=tb.name, callback_data=f"delbox_{tb.id}")] for tb in toolboxes]
        await callback.message.answer("Оберіть ящик для видалення:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(F.data.startswith("delbox_"))
async def confirm_delete_box(callback: CallbackQuery):
    toolbox_id = int(callback.data.split("_")[1])
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        if toolbox:
            await session.delete(toolbox)
            await session.execute(delete(ToolCheck).where(ToolCheck.toolbox_id == toolbox_id))
            await session.execute(delete(BoxStatus).where(BoxStatus.toolbox_id == toolbox_id))
            await session.commit()
            await callback.message.answer(f"🗑️ Ящик '{toolbox.name}' видалено.")
        else:
            await callback.message.answer("❌ Ящик не знайдено.")
    await callback.answer()

@router.message(F.text == "📊 Глобальна статистика")
async def global_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ заборонено")
        return
    
    async with async_session() as session:
        users = await session.execute(select(User))
        users = users.scalars().all()
        checks = await session.execute(select(ToolCheck))
        checks = checks.scalars().all()
        boxes = await session.execute(select(Toolbox))
        boxes = boxes.scalars().all()
        
        stats = f"📊 **ГЛОБАЛЬНА СТАТИСТИКА**\n\n"
        stats += f"👥 Користувачів: {len(users)}\n"
        stats += f"📦 Ящиків: {len(boxes)} / 15\n"
        stats += f"🔧 Перевірок: {len(checks)}\n"
        
        await message.answer(stats, parse_mode="Markdown")
