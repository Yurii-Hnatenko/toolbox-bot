from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, desc
from database import async_session
from models import User, Toolbox, ToolCheck, BoxStatus, ToolImage
from keyboards import main_menu, edit_tools_kb, toolboxes_list_kb
from datetime import datetime
import os

router = Router()

class EditToolsState(StatesGroup):
    selecting_box = State()
    adding_tool = State()
    editing_tool = State()
    adding_photo = State()
    setting_last_user = State()

@router.message(F.text == "📊 Загальний звіт")
async def full_report(message: Message):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        
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
                report += f"🔍 Перша відсутність: {user.full_name} - {first_missing.tool_name} ({first_missing.timestamp.strftime('%d.%m.%Y %H:%M')})\n"
            report += "\n"
        
        await message.answer(report)

@router.message(F.text == "🏷️ Змінити останнього користувача")
async def change_last_user(message: Message, state: FSMContext):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        await state.set_state(EditToolsState.setting_last_user)
        await message.answer("Оберіть ящик:", reply_markup=toolboxes_list_kb(toolboxes, "lastuser"))

@router.callback_query(F.data.startswith("lastuser_"))
async def ask_last_user(callback: CallbackQuery, state: FSMContext):
    toolbox_id = int(callback.data.split("_")[1])
    await state.update_data(toolbox_id=toolbox_id)
    await callback.message.answer("Введіть ПІБ останнього користувача, який брав інструмент:")
    await callback.answer()

@router.message(EditToolsState.setting_last_user)
async def save_last_user(message: Message, state: FSMContext):
    data = await state.get_data()
    async with async_session() as session:
        box_status = await session.execute(select(BoxStatus).where(BoxStatus.toolbox_id == data["toolbox_id"]))
        box_status = box_status.scalar_one_or_none()
        if box_status:
            box_status.last_user = message.text
            await session.commit()
            await message.answer(f"✅ Оновлено: останній користувач - {message.text}")
        else:
            await message.answer("❌ Статус ящика не знайдено")
    await state.clear()

@router.message(F.text == "📸 Фото інструментів")
async def view_tool_photos(message: Message):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        await message.answer("Оберіть ящик:", reply_markup=toolboxes_list_kb(toolboxes, "photos"))

@router.callback_query(F.data.startswith("photos_"))
async def show_tools_for_photo(callback: CallbackQuery):
    toolbox_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        tools = toolbox.get_tools()
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📷 {tool}", callback_data=f"view_photo_{toolbox_id}_{tool}")] for tool in tools
        ])
        
        await callback.message.answer(f"📸 Фото інструментів у {toolbox.name}:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("view_photo_"))
async def show_photo(callback: CallbackQuery):
    _, toolbox_id, tool_name = callback.data.split("_", 2)
    async with async_session() as session:
        photo = await session.execute(
            select(ToolImage).where(ToolImage.toolbox_id == int(toolbox_id), ToolImage.tool_name == tool_name)
            .order_by(desc(ToolImage.uploaded_at)).limit(1)
        )
        photo = photo.scalar_one_or_none()
        
        if photo and os.path.exists(photo.photo_path):
            await callback.message.answer_photo(photo=FSInputFile(photo.photo_path), caption=f"🔧 {tool_name}")
        else:
            await callback.message.answer(f"❌ Фото для {tool_name} відсутнє")
    await callback.answer()

@router.message(F.text == "🔧 Керування інструментами")
async def manage_tools_menu(message: Message, state: FSMContext):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        await state.set_state(EditToolsState.selecting_box)
        await message.answer("Оберіть ящик для редагування:", reply_markup=toolboxes_list_kb(toolboxes, "edittools"))

@router.callback_query(F.data.startswith("edittools_"))
async def edit_tools_list(callback: CallbackQuery, state: FSMContext):
    toolbox_id = int(callback.data.split("_")[1])
    await state.update_data(toolbox_id=toolbox_id)
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        tools = toolbox.get_tools()
        
        if not tools:
            await callback.message.answer(f"📦 {toolbox.name}\nІнструменти відсутні. Додайте перший інструмент.")
            await state.update_data(adding_tool=True)
            await state.set_state(EditToolsState.adding_tool)
            await callback.message.answer("Введіть назву інструменту:")
        else:
            await callback.message.answer(f"📦 {toolbox.name}\nСписок інструментів:", reply_markup=edit_tools_kb(toolbox_id, tools))
    await callback.answer()

@router.callback_query(F.data.startswith("add_tool_"))
async def start_add_tool(callback: CallbackQuery, state: FSMContext):
    toolbox_id = int(callback.data.split("_")[2])
    await state.update_data(toolbox_id=toolbox_id, adding_tool=True)
    await state.set_state(EditToolsState.adding_tool)
    await callback.message.answer("Введіть назву нового інструменту:")
    await callback.answer()

@router.message(EditToolsState.adding_tool)
async def add_tool(message: Message, state: FSMContext):
    data = await state.get_data()
    new_tool = message.text.strip()
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, data["toolbox_id"])
        tools = toolbox.get_tools()
        if new_tool not in tools:
            tools.append(new_tool)
            toolbox.set_tools(tools)
            await session.commit()
            await message.answer(f"✅ Інструмент '{new_tool}' додано до {toolbox.name}")
        else:
            await message.answer(f"⚠️ Інструмент '{new_tool}' вже існує")
        
        await message.answer(f"Оновлений список {toolbox.name}:", reply_markup=edit_tools_kb(toolbox.id, tools))
    await state.clear()

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
    new_name = message.text.strip()
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, data["toolbox_id"])
        tools = toolbox.get_tools()
        if data["old_tool_name"] in tools:
            idx = tools.index(data["old_tool_name"])
            tools[idx] = new_name
            toolbox.set_tools(tools)
            await session.commit()
            await message.answer(f"✅ Перейменовано '{data['old_tool_name']}' → '{new_name}'")
            await message.answer(f"Оновлений список {toolbox.name}:", reply_markup=edit_tools_kb(toolbox.id, tools))
        else:
            await message.answer("❌ Інструмент не знайдено")
    await state.clear()

@router.callback_query(F.data.startswith("del_tool_"))
async def delete_tool(callback: CallbackQuery):
    _, toolbox_id, tool_name = callback.data.split("_", 2)
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, int(toolbox_id))
        tools = toolbox.get_tools()
        if tool_name in tools:
            tools.remove(tool_name)
            toolbox.set_tools(tools)
            await session.commit()
            await callback.message.answer(f"🗑️ Видалено інструмент '{tool_name}'")
            await callback.message.answer(f"Оновлений список {toolbox.name}:", reply_markup=edit_tools_kb(toolbox.id, tools))
        else:
            await callback.message.answer("❌ Інструмент не знайдено")
    await callback.answer()

@router.callback_query(F.data == "back_to_boxes")
async def back_to_boxes(callback: CallbackQuery, state: FSMContext):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        await callback.message.answer("Оберіть ящик:", reply_markup=toolboxes_list_kb(toolboxes, "edittools"))
    await callback.answer()