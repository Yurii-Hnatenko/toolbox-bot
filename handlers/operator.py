from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, desc
from database import async_session
from models import User, Toolbox, ToolCheck, BoxStatus
from keyboards import main_menu, toolboxes_list_kb
from datetime import datetime
import os

router = Router()

class CheckState(StatesGroup):
    selecting_toolbox = State()
    selecting_tool = State()
    comment = State()
    photo = State()

@router.message(F.text == "📋 Перевірити ящик")
async def select_toolbox(message: Message, state: FSMContext):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        if not toolboxes:
            await message.answer("❌ Немає створених ящиків. Зверніться до адміністратора.")
            return
        await state.set_state(CheckState.selecting_toolbox)
        await message.answer("Оберіть ящик:", reply_markup=toolboxes_list_kb(toolboxes, "check"))

@router.callback_query(F.data.startswith("check_"))
async def start_check(callback: CallbackQuery, state: FSMContext):
    toolbox_id = int(callback.data.split("_")[1])
    await state.update_data(toolbox_id=toolbox_id)
    
    async with async_session() as session:
        toolbox = await session.get(Toolbox, toolbox_id)
        tools = toolbox.get_tools()
        if not tools:
            await callback.message.answer("❌ У цьому ящику ще немає інструментів. Механік має їх додати.")
            await callback.answer()
            return
        
        await state.update_data(tools=tools, current_index=0, results=[])
        await state.set_state(CheckState.selecting_tool)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Є", callback_data="present_yes")],
            [InlineKeyboardButton(text="❌ Немає", callback_data="present_no")]
        ])
        
        await callback.message.answer(f"🔧 **{toolbox.name}**\n📌 Інструмент: *{tools[0]}*\n\nОберіть статус:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.in_(["present_yes", "present_no"]))
async def process_presence(callback: CallbackQuery, state: FSMContext):
    is_present = callback.data == "present_yes"
    data = await state.get_data()
    tools = data["tools"]
    index = data["current_index"]
    
    await state.update_data(current_result={"tool": tools[index], "present": is_present})
    await state.set_state(CheckState.comment)
    
    # Клавіатура з кнопкою пропуску коментаря
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустити коментар", callback_data="skip_comment")]
    ])
    
    await callback.message.answer(
        f"📝 **{tools[index]}**\n\nВведіть коментар (або натисніть кнопку нижче):",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "skip_comment")
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    """Пропуск коментаря"""
    data = await state.get_data()
    current_result = data.get("current_result", {})
    current_result["comment"] = ""
    results = data.get("results", [])
    results.append(current_result)
    await state.update_data(results=results)
    
    tools = data["tools"]
    index = data["current_index"] + 1
    
    if index < len(tools):
        await state.update_data(current_index=index)
        await state.set_state(CheckState.selecting_tool)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Є", callback_data="present_yes")],
            [InlineKeyboardButton(text="❌ Немає", callback_data="present_no")]
        ])
        
        await callback.message.answer(
            f"📌 **Наступний інструмент:** *{tools[index]}*\n\nОберіть статус:",
            reply_markup=kb,
            parse_mode="Markdown"
        )
    else:
        await state.set_state(CheckState.photo)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустити фото", callback_data="skip_photo")]
        ])
        await callback.message.answer(
            "📸 **Фото ящика**\n\nНадішліть фото (або натисніть кнопку нижче):",
            reply_markup=kb,
            parse_mode="Markdown"
        )
    await callback.answer()

@router.message(CheckState.comment)
async def process_comment(message: Message, state: FSMContext):
    comment = message.text.strip()
    data = await state.get_data()
    current_result = data.get("current_result", {})
    current_result["comment"] = comment
    results = data.get("results", [])
    results.append(current_result)
    await state.update_data(results=results)
    
    tools = data["tools"]
    index = data["current_index"] + 1
    
    if index < len(tools):
        await state.update_data(current_index=index)
        await state.set_state(CheckState.selecting_tool)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Є", callback_data="present_yes")],
            [InlineKeyboardButton(text="❌ Немає", callback_data="present_no")]
        ])
        
        await message.answer(
            f"📌 **Наступний інструмент:** *{tools[index]}*\n\nОберіть статус:",
            reply_markup=kb,
            parse_mode="Markdown"
        )
    else:
        await state.set_state(CheckState.photo)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустити фото", callback_data="skip_photo")]
        ])
        await message.answer(
            "📸 **Фото ящика**\n\nНадішліть фото (або натисніть кнопку нижче):",
            reply_markup=kb,
            parse_mode="Markdown"
        )

@router.callback_query(F.data == "skip_photo")
async def skip_photo(callback: CallbackQuery, state: FSMContext):
    """Пропуск фото - використовуємо callback.message замість message"""
    data = await state.get_data()
    results = data.get("results", [])
    toolbox_id = data["toolbox_id"]
    
    async with async_session() as session:
        user = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = user.scalar_one()
        
        all_present = True
        for res in results:
            check = ToolCheck(
                toolbox_id=toolbox_id,
                user_id=user.id,
                tool_name=res["tool"],
                is_present=res["present"],
                comment=res.get("comment", ""),
                photo_path=None
            )
            session.add(check)
            if not res["present"]:
                all_present = False
        
        box_status = await session.execute(select(BoxStatus).where(BoxStatus.toolbox_id == toolbox_id))
        box_status = box_status.scalar_one_or_none()
        if not box_status:
            box_status = BoxStatus(toolbox_id=toolbox_id)
            session.add(box_status)
        
        box_status.last_check_time = datetime.utcnow()
        box_status.last_check_user = user.id
        box_status.is_complete = all_present
        
        await session.commit()
    
    # Підрахунок результатів
    total = len(results)
    present_count = sum(1 for r in results if r["present"])
    missing_count = total - present_count
    
    result_text = f"✅ **Перевірку завершено!**\n\n"
    result_text += f"📊 **Результати:**\n"
    result_text += f"   ✅ Є в наявності: {present_count}/{total}\n"
    result_text += f"   ❌ Відсутні: {missing_count}/{total}\n"
    
    if missing_count > 0:
        result_text += f"\n⚠️ **Відсутні інструменти:**\n"
        for r in results:
            if not r["present"]:
                result_text += f"   • {r['tool']}\n"
                if r.get("comment"):
                    result_text += f"     📝 {r['comment']}\n"
    
    await callback.message.answer(result_text, parse_mode="Markdown", reply_markup=main_menu("operator"))
    await state.clear()
    await callback.answer()

@router.message(CheckState.photo)
async def save_photo_and_check(message: Message, state: FSMContext):
    photo_path = None
    if message.photo:
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        os.makedirs("media", exist_ok=True)
        photo_path = f"media/{file.file_id}.jpg"
        await message.bot.download_file(file.file_path, photo_path)
    
    # Зберігаємо з фото
    data = await state.get_data()
    results = data.get("results", [])
    toolbox_id = data["toolbox_id"]
    
    async with async_session() as session:
        user = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user.scalar_one()
        
        all_present = True
        for res in results:
            check = ToolCheck(
                toolbox_id=toolbox_id,
                user_id=user.id,
                tool_name=res["tool"],
                is_present=res["present"],
                comment=res.get("comment", ""),
                photo_path=photo_path
            )
            session.add(check)
            if not res["present"]:
                all_present = False
        
        box_status = await session.execute(select(BoxStatus).where(BoxStatus.toolbox_id == toolbox_id))
        box_status = box_status.scalar_one_or_none()
        if not box_status:
            box_status = BoxStatus(toolbox_id=toolbox_id)
            session.add(box_status)
        
        box_status.last_check_time = datetime.utcnow()
        box_status.last_check_user = user.id
        box_status.is_complete = all_present
        
        await session.commit()
    
    # Підрахунок результатів
    total = len(results)
    present_count = sum(1 for r in results if r["present"])
    missing_count = total - present_count
    
    result_text = f"✅ **Перевірку завершено!**\n\n"
    result_text += f"📊 **Результати:**\n"
    result_text += f"   ✅ Є в наявності: {present_count}/{total}\n"
    result_text += f"   ❌ Відсутні: {missing_count}/{total}\n"
    
    if missing_count > 0:
        result_text += f"\n⚠️ **Відсутні інструменти:**\n"
        for r in results:
            if not r["present"]:
                result_text += f"   • {r['tool']}\n"
                if r.get("comment"):
                    result_text += f"     📝 {r['comment']}\n"
    
    if photo_path:
        result_text += f"\n📸 Фото збережено!"
    
    await message.answer(result_text, parse_mode="Markdown", reply_markup=main_menu("operator"))
    await state.clear()

@router.message(F.text == "📜 Історія моїх перевірок")
async def my_history(message: Message):
    async with async_session() as session:
        user = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user.scalar_one()
        
        checks = await session.execute(
            select(ToolCheck).where(ToolCheck.user_id == user.id)
            .order_by(desc(ToolCheck.timestamp)).limit(20)
        )
        checks = checks.scalars().all()
        
        if not checks:
            await message.answer("📭 У вас ще немає перевірок.")
            return
        
        text = "📜 **Історія ваших перевірок:**\n\n"
        for ch in checks:
            toolbox = await session.get(Toolbox, ch.toolbox_id)
            text += f"📦 **{toolbox.name}**\n"
            text += f"   🔧 {ch.tool_name}: {'✅' if ch.is_present else '❌'}\n"
            text += f"   🕐 {ch.timestamp.strftime('%d.%m.%Y %H:%M:%S')}\n"
            if ch.comment:
                text += f"   📝 {ch.comment}\n"
            text += "   ---\n\n"
        
        await message.answer(text, parse_mode="Markdown")