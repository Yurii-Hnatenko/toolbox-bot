from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from database import async_session
from models import User, Toolbox, BoxStatus, ToolCheck
from keyboards import toolboxes_list_kb, main_menu_by_role
from handlers.common import active_role

router = Router()

@router.message(F.text == "📊 Загальний звіт")
async def full_report(message: Message):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        
        if not toolboxes:
            await message.answer("❌ Немає створених ящиків.")
            return
        
        report = "📊 ЗВІТ ПО ВСІХ ЯЩИКАХ\n\n"
        for box in toolboxes:
            status = await session.execute(select(BoxStatus).where(BoxStatus.toolbox_id == box.id))
            status = status.scalar_one_or_none()
            
            first_missing = await session.execute(
                select(ToolCheck).where(ToolCheck.toolbox_id == box.id, ToolCheck.is_present == False)
                .order_by(ToolCheck.timestamp).limit(1)
            )
            first_missing = first_missing.scalar_one_or_none()
            
            last_user = status.last_user if status else "Невідомо"
            
            report += f"📦 {box.name}\n"
            report += f"Стан: {'✅ Укомплектовано' if status and status.is_complete else '❌ Не укомплектовано'}\n"
            report += f"🕐 Остання перевірка: {status.last_check_time.strftime('%d.%m.%Y %H:%M') if status and status.last_check_time else 'Немає'}\n"
            report += f"👤 Останній користувач: {last_user}\n"
            if first_missing:
                user = await session.get(User, first_missing.user_id)
                report += f"🔍 Перша відсутність: {user.full_name} - {first_missing.tool_name}\n"
            report += "\n"
        await message.answer(report)

@router.message(F.text == "🔧 Керування інструментами")
async def manage_tools(message: Message):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        if not toolboxes:
            await message.answer("❌ Немає створених ящиків.")
            return
        await message.answer("Оберіть ящик:", reply_markup=toolboxes_list_kb(toolboxes, "edittools"))
