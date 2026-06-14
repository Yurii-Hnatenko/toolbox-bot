from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from database import async_session
from models import User
from keyboards import main_menu_by_role
from config import ADMIN_IDS
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)
router = Router()

# Глобальний словник для зберігання активної ролі
active_role = {}

@router.message(Command("start"))
async def cmd_start(message: Message):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        if not user:
            if message.from_user.id in ADMIN_IDS:
                role = "admin,mechanic,operator"
                logger.info(f"Адмін {message.from_user.id} отримав всі ролі")
            else:
                role = "operator"
                logger.info(f"Користувач {message.from_user.id} отримав роль оператора")
            
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username or "",
                full_name=message.from_user.full_name,
                role=role
            )
            session.add(user)
            await session.commit()
        
        if message.from_user.id not in active_role:
            active_role[message.from_user.id] = user.primary_role
        
        await message.answer(
            f"👋 Вітаю, {message.from_user.full_name}!\n\n"
            f"📋 Ваші ролі: {', '.join(user.role_list)}\n"
            f"⭐ Активна роль: {active_role.get(message.from_user.id, user.primary_role).capitalize()}\n\n"
            f"Оберіть дію з меню:",
            reply_markup=main_menu_by_role(active_role.get(message.from_user.id, user.primary_role))
        )

@router.message(F.text == "ℹ️ Інформація")
async def info(message: Message):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Користувача не знайдено")
            return
        
        await message.answer(
            f"👤 **Інформація про користувача**\n\n"
            f"📛 Ім'я: {user.full_name}\n"
            f"🆔 Telegram ID: {user.telegram_id}\n"
            f"🔧 Всі ролі: {', '.join(user.role_list)}\n"
            f"⚡ Активна роль: {active_role.get(message.from_user.id, user.primary_role).capitalize()}\n"
            f"📅 ID в системі: {user.id}",
            parse_mode="Markdown"
        )

@router.message(F.text == "🔙 На головну")
async def back_to_main(message: Message):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Користувача не знайдено")
            return
        
        current_role = active_role.get(message.from_user.id, user.primary_role)
        
        await message.answer(
            "🔙 Повернення до головного меню:",
            reply_markup=main_menu_by_role(current_role)
        )
