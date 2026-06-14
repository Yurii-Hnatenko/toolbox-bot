import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from database import async_session
from models import User, Toolbox, BoxStatus, ToolCheck, ToolImage
from keyboards import toolboxes_list_kb, main_menu_by_role
from handlers.common import active_role

router = Router()

class EditToolsState(StatesGroup):
    selecting_toolbox = State()
    adding_tool = State()
    editing_tool = State()

class LastUserState(StatesGroup):
    selecting_box = State()
    entering_name = State()

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
    toolbox_id = int(callback.data.split("_")[1])
    await state.update_data(toolbox_id=toolbox_id)
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        tools = toolbox.get_tools()
        
        if not tools:
            await callback.message.answer(f"📦 {toolbox.name}\nІнструменти відсутні. Додайте перший.")
            await state.set_state(EditToolsState.adding_tool)
            await callback.message.answer("Введіть назву інструменту:")
        else:
            buttons = []
            for tool in tools:
                buttons.append([InlineKeyboardButton(text=f"✏️ {tool}", callback_data=f"edit_tool_{toolbox_id}_{tool}")])
                buttons.append([InlineKeyboardButton(text=f"🗑️ Видалити {tool}", callback_data=f"del_tool_{toolbox_id}_{tool}")])
            buttons.append([InlineKeyboardButton(text="➕ Додати інструмент", callback_data=f"add_tool_{toolbox_id}")])
            buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_boxes")])
            
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
    toolbox_id = int(callback.data.split("_")[2])
    await state.update_data(toolbox_id=toolbox_id)
    await state.set_state(EditToolsState.adding_tool)
    await callback.message.answer("Введіть назву нового інструменту:")
    await callback.answer()

@router.message(EditToolsState.adding_tool)
async def add_tool(message: Message, state: FSMContext):
    data = await state.get_data()
    toolbox_id = data.get("toolbox_id")
    new_tool = message.text.strip()
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        tools = toolbox.get_tools()
        
        if new_tool not in tools:
            tools.append(new_tool)
            toolbox.set_tools(tools)
            await session.commit()
            await message.answer(f"✅ Інструмент '{new_tool}' додано.")
        else:
            await message.answer(f"⚠️ '{new_tool}' вже існує.")
    
    await state.clear()
    await edit_tools_list(message, state)

@router.callback_query(F.data.startswith("edit_tool_"))
async def edit_tool(callback: CallbackQuery, state: FSMContext):
    _, toolbox_id, old_name = callback.data.split("_", 2)
    await state.update_data(toolbox_id=int(toolbox_id), old_tool_name=old_name)
    await state.set_state(EditToolsState.editing_tool)
    await callback.message.answer(f"Введіть нову назву для '{old_name}':")
    await callback.answer()

@router.message(EditToolsState.editing_tool)
async def save_edited_tool(message: Message, state: FSMContext):
    data = await state.get_data()
    toolbox_id = data.get("toolbox_id")
    old_name = data.get("old_tool_name")
    new_name = message.text.strip()
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        tools = toolbox.get_tools()
        
        if old_name in tools:
            idx = tools.index(old_name)
            tools[idx] = new_name
            toolbox.set_tools(tools)
            await session.commit()
            await message.answer(f"✅ Перейменовано '{old_name}' → '{new_name}'")
        else:
            await message.answer("❌ Інструмент не знайдено.")
    
    await state.clear()
    await edit_tools_list(message, state)

@router.callback_query(F.data.startswith("del_tool_"))
async def delete_tool(callback: CallbackQuery):
    _, toolbox_id, tool_name = callback.data.split("_", 2)
    toolbox_id = int(toolbox_id)
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        tools = toolbox.get_tools()
        
        if tool_name in tools:
            tools.remove(tool_name)
            toolbox.set_tools(tools)
            await session.commit()
            await callback.message.answer(f"🗑️ Інструмент '{tool_name}' видалено.")
    
    await callback.answer()
    await edit_tools_list(callback, FSMContext())

@router.message(F.text == "📊 Загальний звіт")
async def full_report(message: Message):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        
        if not toolboxes:
            await message.answer("❌ Немає ящиків.")
            return
        
        report = "📊 ЗВІТ ПО ВСІХ ЯЩИКАХ\n\n"
        for box in toolboxes:
            status = await session.execute(select(BoxStatus).where(BoxStatus.toolbox_id == box.id))
            status = status.scalar_one_or_none()
            
            report += f"📦 {box.name}: {'✅ Укомплектовано' if status and status.is_complete else '❌ Не укомплектовано'}\n"
            if status and status.last_user:
                report += f"👤 Останній користувач: {status.last_user}\n"
            report += "\n"
        
        await message.answer(report)

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
    toolbox_id = int(callback.data.split("_")[1])
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
    toolbox_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        tools = toolbox.get_tools()
        
        if not tools:
            await callback.message.answer("❌ Немає інструментів.")
            await callback.answer()
            return
        
        buttons = [[InlineKeyboardButton(text=f"📷 {tool}", callback_data=f"view_photo_{toolbox_id}_{tool}")] for tool in tools]
        await callback.message.answer(f"📸 Оберіть інструмент:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()
