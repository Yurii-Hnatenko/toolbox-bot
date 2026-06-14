from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, delete
from database import async_session
from models import User, Toolbox, ToolCheck, BoxStatus
from keyboards import main_menu_by_role
from config import ADMIN_IDS
from handlers.common import active_role

router = Router()

class AdminState(StatesGroup):
    adding_toolbox = State()

@router.message(F.text == "👥 Керування ролями")
async def manage_roles(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ заборонено")
        return
    await message.answer("Надішліть Telegram ID користувача для зміни ролей (поки що в розробці)")

@router.message(F.text == "📦 Керування ящиками")
async def manage_boxes(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ заборонено")
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Додати ящик", callback_data="add_toolbox")],
        [InlineKeyboardButton(text="❌ Видалити ящик", callback_data="delete_toolbox")]
    ])
    await message.answer("Керування ящиками:", reply_markup=kb)

@router.callback_query(F.data == "add_toolbox")
async def add_toolbox(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.adding_toolbox)
    await callback.message.answer("Введіть назву нового ящика:")
    await callback.answer()

@router.message(AdminState.adding_toolbox)
async def save_new_toolbox(message: Message, state: FSMContext):
    name = message.text.strip()
    async with async_session() as session:
        existing = await session.execute(select(Toolbox).where(Toolbox.name == name))
        if existing.scalar_one_or_none():
            await message.answer("❌ Ящик з такою назвою вже існує")
        else:
            new_box = Toolbox(name=name)
            new_box.set_tools([])
            session.add(new_box)
            await session.commit()
            await message.answer(f"✅ Ящик '{name}' створено")
    await state.clear()

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
        
        stats = f"📊 ГЛОБАЛЬНА СТАТИСТИКА\n\n"
        stats += f"👥 Користувачів: {len(users)}\n"
        stats += f"📦 Ящиків: {len(boxes)} / 15\n"
        stats += f"🔧 Перевірок: {len(checks)}\n"
        await message.answer(stats)
