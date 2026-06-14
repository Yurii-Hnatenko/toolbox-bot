import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from database import async_session
from models import User, Toolbox, BoxStatus, ToolCheck, ToolImage
from keyboards import toolboxes_list_kb, main_menu_by_role, report_boxes_list_kb
from handlers.common import active_role

router = Router()

class EditToolsState(StatesGroup):
    selecting_toolbox = State()
    adding_tool = State()
    editing_tool = State()

class LastUserState(StatesGroup):
    selecting_box = State()
    entering_name = State()

def safe_int(value, default=None):
    """Безпечне перетворення на int"""
    try:
        return int(value)
    except (ValueError, TypeError, IndexError):
        return default

@router.message(F.text == "🔧 Керування інструментами")
async def manage_tools(message: Message, state: FSMContext):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        if not toolboxes:
            await message.answer("❌ Немає ящиків.")
            return
        await state.set_state(EditToolsState.selecting_toolbox)
        await message.answer("Оберіть ящик:", reply_markup=toolboxes_list_kb(toolboxes, "edittools"))

@router.callback_query(F.data.startswith("edittools_"))
async def edit_tools_list(callback: CallbackQuery, state: FSMContext):
    toolbox_id = safe_int(callback.data.split("_")[1])
    if toolbox_id is None:
        await callback.answer("Помилка: невірний формат даних")
        return
    
    await state.update_data(toolbox_id=toolbox_id)
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        if not toolbox:
            await callback.message.answer("❌ Ящик не знайдено")
            await callback.answer()
            return
        
        tools = toolbox.get_tools()
        
        if not tools:
            await callback.message.answer(f"📦 {toolbox.name}\nІнструменти відсутні. Додайте перший.")
            await state.set_state(EditToolsState.adding_tool)
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Скасувати", callback_data="cancel_add_tool")]
            ])
            await callback.message.answer(
                "✏️ Введіть назву нового інструменту:\n\n_Надішліть назву або натисніть Скасувати_",
                reply_markup=kb,
                parse_mode="Markdown"
            )
        else:
            buttons = []
            for tool in tools:
                buttons.append([InlineKeyboardButton(text=f"✏️ {tool}", callback_data=f"edit_tool_{toolbox_id}_{tool}")])
                buttons.append([InlineKeyboardButton(text=f"🗑️ Видалити {tool}", callback_data=f"del_tool_{toolbox_id}_{tool}")])
            buttons.append([InlineKeyboardButton(text="➕ Додати інструмент", callback_data=f"add_tool_{toolbox_id}")])
            buttons.append([InlineKeyboardButton(text="🔙 Назад до вибору ящика", callback_data="back_to_boxes")])
            
            await callback.message.answer(
                f"📦 {toolbox.name}\nОберіть дію:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
    await callback.answer()

@router.callback_query(F.data == "back_to_boxes")
async def back_to_boxes(callback: CallbackQuery, state: FSMContext):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        await state.set_state(EditToolsState.selecting_toolbox)
        await callback.message.answer("Оберіть ящик:", reply_markup=toolboxes_list_kb(toolboxes, "edittools"))
    await callback.answer()

@router.callback_query(F.data.startswith("add_tool_"))
async def start_add_tool(callback: CallbackQuery, state: FSMContext):
    toolbox_id = safe_int(callback.data.split("_")[2])
    if toolbox_id is None:
        await callback.answer("Помилка: невірний формат даних")
        return
    
    await state.update_data(toolbox_id=toolbox_id)
    await state.set_state(EditToolsState.adding_tool)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Скасувати", callback_data="cancel_add_tool")]
    ])
    
    await callback.message.answer(
        "✏️ Введіть назву нового інструменту:\n\n_Надішліть назву або натисніть Скасувати_",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_add_tool")
async def cancel_add_tool(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await edit_tools_list(callback, state)
    await callback.answer("❌ Додавання інструменту скасовано")

@router.message(EditToolsState.adding_tool)
async def add_tool(message: Message, state: FSMContext):
    data = await state.get_data()
    toolbox_id = data.get("toolbox_id")
    new_tool = message.text.strip()
    
    if new_tool.lower() == "скасувати":
        await message.answer("❌ Додавання інструменту скасовано.")
        await state.clear()
        await edit_tools_list(message, state)
        return
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        if not toolbox:
            await message.answer("❌ Ящик не знайдено")
            await state.clear()
            return
        
        tools = toolbox.get_tools()
        
        if new_tool in tools:
            await message.answer(f"⚠️ Інструмент '{new_tool}' вже існує в ящику '{toolbox.name}'. Введіть іншу назву:")
            return
        else:
            tools.append(new_tool)
            toolbox.set_tools(tools)
            await session.commit()
            await message.answer(f"✅ Інструмент '{new_tool}' додано до ящика '{toolbox.name}'!")
    
    await state.clear()
    await edit_tools_list(message, state)

@router.callback_query(F.data.startswith("edit_tool_"))
async def edit_tool(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer("Помилка: невірний формат даних")
        return
    
    toolbox_id = safe_int(parts[2])
    old_name = "_".join(parts[3:])
    
    if toolbox_id is None:
        await callback.answer("Помилка: невірний формат даних")
        return
    
    await state.update_data(toolbox_id=toolbox_id, old_tool_name=old_name)
    await state.set_state(EditToolsState.editing_tool)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Скасувати", callback_data="cancel_edit_tool")]
    ])
    
    await callback.message.answer(
        f"✏️ Введіть нову назву для інструменту '{old_name}':\n\n_Надішліть назву або натисніть Скасувати_",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_edit_tool")
async def cancel_edit_tool(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await edit_tools_list(callback, state)
    await callback.answer("❌ Редагування інструменту скасовано")

@router.message(EditToolsState.editing_tool)
async def save_edited_tool(message: Message, state: FSMContext):
    data = await state.get_data()
    toolbox_id = data.get("toolbox_id")
    old_name = data.get("old_tool_name")
    new_name = message.text.strip()
    
    if new_name.lower() == "скасувати":
        await message.answer("❌ Редагування інструменту скасовано.")
        await state.clear()
        await edit_tools_list(message, state)
        return
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        if not toolbox:
            await message.answer("❌ Ящик не знайдено")
            await state.clear()
            return
        
        tools = toolbox.get_tools()
        
        if old_name in tools:
            if new_name in tools and new_name != old_name:
                await message.answer(f"⚠️ Інструмент '{new_name}' вже існує. Введіть іншу назву:")
                return
            idx = tools.index(old_name)
            tools[idx] = new_name
            toolbox.set_tools(tools)
            await session.commit()
            await message.answer(f"✅ Інструмент '{old_name}' перейменовано на '{new_name}'")
        else:
            await message.answer("❌ Інструмент не знайдено.")
    
    await state.clear()
    await edit_tools_list(message, state)

@router.callback_query(F.data.startswith("del_tool_"))
async def delete_tool(callback: CallbackQuery):
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer("Помилка: невірний формат даних")
        return
    
    toolbox_id = safe_int(parts[2])
    tool_name = "_".join(parts[3:])
    
    if toolbox_id is None:
        await callback.answer("Помилка: невірний формат даних")
        return
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        if not toolbox:
            await callback.message.answer("❌ Ящик не знайдено")
            await callback.answer()
            return
        
        tools = toolbox.get_tools()
        
        if tool_name in tools:
            tools.remove(tool_name)
            toolbox.set_tools(tools)
            await session.commit()
            await callback.message.answer(f"🗑️ Інструмент '{tool_name}' видалено.")
    
    await callback.answer()
    await edit_tools_list(callback, FSMContext())

# ==================== ЗВІТИ ====================
@router.message(F.text == "📊 Загальний звіт")
async def full_report(message: Message):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        
        if not toolboxes:
            await message.answer("❌ Немає створених ящиків.")
            return
        
        report = "📊 **ЗВІТ ПО ВСІХ ІНСТРУМЕНТАЛЬНИХ ЯЩИКАХ**\n"
        report += "━" * 30 + "\n\n"
        
        for box in toolboxes:
            status = await session.execute(select(BoxStatus).where(BoxStatus.toolbox_id == box.id))
            status = status.scalar_one_or_none()
            
            tools = box.get_tools()
            
            last_checks = {}
            if tools:
                checks_result = await session.execute(
                    select(ToolCheck).where(ToolCheck.toolbox_id == box.id)
                    .order_by(ToolCheck.timestamp.desc())
                )
                checks = checks_result.scalars().all()
                checked_tools = set()
                for check in checks:
                    if check.tool_name not in checked_tools:
                        last_checks[check.tool_name] = check.is_present
                        checked_tools.add(check.tool_name)
            
            is_complete = status.is_complete if status else True
            status_icon = "✅" if is_complete else "❌"
            status_text = "КОМПЛЕКТНО" if is_complete else "НЕ КОМПЛЕКТНО"
            
            report += f"**📦 ЯЩИК №{box.id}** ─ {box.name}\n"
            report += f"┌─────────────────────────────────\n"
            report += f"│ Статус: {status_icon} {status_text}\n"
            
            if not is_complete:
                missing_tools = []
                for tool in tools:
                    is_present = last_checks.get(tool, False)
                    if not is_present:
                        missing_tools.append(tool)
                
                if missing_tools:
                    report += f"│\n│ ❌ **Відсутні інструменти:**\n"
                    for tool in missing_tools:
                        report += f"│    • {tool}\n"
                    
                    first_missing = await session.execute(
                        select(ToolCheck).where(
                            ToolCheck.toolbox_id == box.id, 
                            ToolCheck.is_present == False
                        ).order_by(ToolCheck.timestamp).limit(1)
                    )
                    first_missing = first_missing.scalar_one_or_none()
                    
                    if first_missing:
                        user = await session.get(User, first_missing.user_id)
                        user_name = user.full_name if user else "Невідомо"
                        report += f"│\n│ 🔍 **Вперше виявив відсутність:**\n"
                        report += f"│    👤 {user_name}\n"
                        report += f"│    🕐 {first_missing.timestamp.strftime('%d.%m.%Y о %H:%M')}\n"
                else:
                    report += f"│\n│ ⚠️ Немає даних про перевірку\n"
                    report += f"│    Проведіть перевірку ящика\n"
            else:
                report += f"│\n│ ✅ Всі інструменти на місці\n"
            
            if status and status.last_check_time:
                last_check_date = status.last_check_time.strftime('%d.%m.%Y %H:%M')
                report += f"│\n│ 🕐 Остання перевірка: {last_check_date}\n"
            
            if status and status.last_user:
                report += f"│ 👤 Останній користувач: {status.last_user}\n"
            
            report += f"└─────────────────────────────────\n\n"
        
        await message.answer(report, parse_mode="Markdown")

@router.message(F.text == "📋 Детальний звіт")
async def detail_report_menu(message: Message):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        if not toolboxes:
            await message.answer("❌ Немає створених ящиків.")
            return
        await message.answer("Оберіть ящик для детального звіту:", reply_markup=report_boxes_list_kb(toolboxes))

@router.callback_query(F.data.startswith("report_"))
async def box_detail_report(callback: CallbackQuery):
    toolbox_id = safe_int(callback.data.split("_")[1])
    if toolbox_id is None:
        await callback.answer("Помилка: невірний формат даних")
        return
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        if not toolbox:
            await callback.message.answer("❌ Ящик не знайдено")
            await callback.answer()
            return
        
        status = await session.execute(select(BoxStatus).where(BoxStatus.toolbox_id == toolbox_id))
        status = status.scalar_one_or_none()
        
        tools = toolbox.get_tools()
        
        last_checks = {}
        if tools:
            checks_result = await session.execute(
                select(ToolCheck).where(ToolCheck.toolbox_id == toolbox_id)
                .order_by(ToolCheck.timestamp.desc())
            )
            checks = checks_result.scalars().all()
            checked_tools = set()
            for check in checks:
                if check.tool_name not in checked_tools:
                    last_checks[check.tool_name] = check.is_present
                    checked_tools.add(check.tool_name)
        
        is_complete = status.is_complete if status else True
        
        report = f"📦 **ДЕТАЛЬНИЙ ЗВІТ: {toolbox.name}**\n"
        report += "━" * 30 + "\n\n"
        
        report += f"📊 **Загальний стан:**\n"
        report += f"│   {'✅ КОМПЛЕКТНО' if is_complete else '❌ НЕ КОМПЛЕКТНО'}\n\n"
        
        report += f"🔧 **Список інструментів:**\n"
        for tool in tools:
            is_present = last_checks.get(tool, None)
            if is_present is True:
                report += f"│   ✅ {tool}\n"
            elif is_present is False:
                report += f"│   ❌ {tool}\n"
            else:
                report += f"│   ❓ {tool} (немає даних)\n"
        
        if status and status.last_check_time:
            report += f"\n🕐 **Остання перевірка:**\n"
            report += f"│   {status.last_check_time.strftime('%d.%m.%Y о %H:%M')}\n"
        
        if status and status.last_user:
            report += f"\n👤 **Останній користувач:**\n"
            report += f"│   {status.last_user}\n"
        
        await callback.message.answer(report, parse_mode="Markdown")
    await callback.answer()

# ==================== ІНШІ ФУНКЦІЇ ====================
@router.message(F.text == "🏷️ Змінити останнього користувача")
async def change_last_user(message: Message, state: FSMContext):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        if not toolboxes:
            await message.answer("❌ Немає ящиків.")
            return
        await state.set_state(LastUserState.selecting_box)
        await message.answer("Оберіть ящик:", reply_markup=toolboxes_list_kb(toolboxes, "lastuser"))

@router.callback_query(F.data.startswith("lastuser_"))
async def ask_last_user(callback: CallbackQuery, state: FSMContext):
    toolbox_id = safe_int(callback.data.split("_")[1])
    if toolbox_id is None:
        await callback.answer("Помилка: невірний формат даних")
        return
    
    await state.update_data(toolbox_id=toolbox_id)
    await state.set_state(LastUserState.entering_name)
    await callback.message.answer("Введіть ПІБ останнього користувача:")
    await callback.answer()

@router.message(LastUserState.entering_name)
async def save_last_user(message: Message, state: FSMContext):
    data = await state.get_data()
    toolbox_id = data.get("toolbox_id")
    last_user = message.text.strip()
    
    async with async_session() as session:
        box_status = await session.execute(select(BoxStatus).where(BoxStatus.toolbox_id == toolbox_id))
        box_status = box_status.scalar_one_or_none()
        if box_status:
            box_status.last_user = last_user
            await session.commit()
            await message.answer(f"✅ Останнього користувача змінено на {last_user}.")
        else:
            await message.answer("❌ Статус ящика не знайдено.")
    await state.clear()

@router.message(F.text == "📸 Фото інструментів")
async def view_tool_photos_mechanic(message: Message):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        if not toolboxes:
            await message.answer("❌ Немає ящиків.")
            return
        await message.answer("Оберіть ящик:", reply_markup=toolboxes_list_kb(toolboxes, "photos"))

@router.callback_query(F.data.startswith("photos_"))
async def show_tools_for_photo_mechanic(callback: CallbackQuery):
    toolbox_id = safe_int(callback.data.split("_")[1])
    if toolbox_id is None:
        await callback.answer("Помилка: невірний формат даних")
        return
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        if not toolbox:
            await callback.message.answer("❌ Ящик не знайдено")
            await callback.answer()
            return
        
        tools = toolbox.get_tools()
        
        if not tools:
            await callback.message.answer("❌ Немає інструментів.")
            await callback.answer()
            return
        
        buttons = [[InlineKeyboardButton(text=f"📷 {tool}", callback_data=f"view_photo_{toolbox_id}_{tool}")] for tool in tools]
        await callback.message.answer(f"📸 Оберіть інструмент:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(F.data.startswith("view_photo_"))
async def show_photo(callback: CallbackQuery):
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer("Помилка: невірний формат даних")
        return
    
    toolbox_id = safe_int(parts[2])
    tool_name = "_".join(parts[3:])
    
    if toolbox_id is None:
        await callback.answer("Помилка: невірний формат даних")
        return
    
    async with async_session() as session:
        photo = await session.execute(
            select(ToolImage).where(
                ToolImage.toolbox_id == toolbox_id, 
                ToolImage.tool_name == tool_name
            ).order_by(ToolImage.uploaded_at.desc()).limit(1)
        )
        photo = photo.scalar_one_or_none()
        
        if photo and os.path.exists(photo.photo_path):
            await callback.message.answer_photo(
                photo=FSInputFile(photo.photo_path), 
                caption=f"🔧 {tool_name}"
            )
        else:
            await callback.message.answer(f"❌ Фото для {tool_name} відсутнє")
    await callback.answer()
