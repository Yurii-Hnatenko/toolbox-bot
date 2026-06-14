import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, desc
from database import async_session
from models import User, Toolbox, ToolCheck, BoxStatus, ToolImage
from keyboards import toolboxes_list_kb, main_menu_by_role
from handlers.common import active_role
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = Router()

class CheckState(StatesGroup):
    selecting_toolbox = State()
    selecting_tool = State()
    comment = State()
    photo = State()

def safe_int(value, default=None):
    """Безпечне перетворення на int"""
    try:
        return int(value)
    except (ValueError, TypeError, IndexError):
        return default

@router.message(F.text == "📋 Перевірити ящик")
async def select_toolbox(message: Message, state: FSMContext):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        if not toolboxes:
            await message.answer("❌ Немає створених ящиків.")
            return
        await state.set_state(CheckState.selecting_toolbox)
        await message.answer("Оберіть ящик для перевірки:", reply_markup=toolboxes_list_kb(toolboxes, "check"))

@router.callback_query(F.data.startswith("check_"))
async def start_check(callback: CallbackQuery, state: FSMContext):
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
            await callback.message.answer(f"❌ У ящику '{toolbox.name}' немає інструментів.")
            await callback.answer()
            return
        
        await state.update_data(tools=tools, current_index=0, results=[])
        await state.set_state(CheckState.selecting_tool)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Є", callback_data="present_yes")],
            [InlineKeyboardButton(text="❌ Немає", callback_data="present_no")]
        ])
        
        await callback.message.answer(
            f"🔧 **Ящик:** {toolbox.name}\n"
            f"📌 **Інструмент 1/{len(tools)}:** {tools[0]}\n\n"
            f"Оберіть статус:",
            reply_markup=kb,
            parse_mode="Markdown"
        )
    await callback.answer()

@router.callback_query(F.data.in_(["present_yes", "present_no"]))
async def process_presence(callback: CallbackQuery, state: FSMContext):
    is_present = callback.data == "present_yes"
    data = await state.get_data()
    tools = data["tools"]
    index = data["current_index"]
    
    await state.update_data(current_result={"tool": tools[index], "present": is_present})
    await state.set_state(CheckState.comment)
    
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
            f"📌 **Інструмент {index+1}/{len(tools)}:** {tools[index]}\n\nОберіть статус:",
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
            f"📌 **Інструмент {index+1}/{len(tools)}:** {tools[index]}\n\nОберіть статус:",
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
    """Пропуск фото - ВИПРАВЛЕНО"""
    # Спочатку відповідаємо, щоб кнопка не зависала
    await callback.answer("Зберігаю результати перевірки...")
    
    data = await state.get_data()
    results = data.get("results", [])
    toolbox_id = data.get("toolbox_id")
    
    if not results:
        await callback.message.answer("❌ Немає даних про перевірку. Спробуйте ще раз.")
        await state.clear()
        return
    
    try:
        async with async_session() as session:
            # Отримуємо користувача за telegram_id
            user_result = await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                # Якщо користувача немає в БД, створюємо нового
                user = User(
                    telegram_id=callback.from_user.id,
                    username=callback.from_user.username or "",
                    full_name=callback.from_user.full_name or "Користувач",
                    role="operator"
                )
                session.add(user)
                await session.commit()
                logger.info(f"Створено нового користувача: {user.telegram_id}")
            
            # Отримуємо ящик для перевірки
            toolbox = await session.get(Toolbox, toolbox_id)
            if not toolbox:
                await callback.message.answer("❌ Ящик не знайдено")
                await state.clear()
                return
            
            # Зберігаємо результати перевірок
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
            
            # Оновлюємо статус ящика
            box_status_result = await session.execute(
                select(BoxStatus).where(BoxStatus.toolbox_id == toolbox_id)
            )
            box_status = box_status_result.scalar_one_or_none()
            if not box_status:
                box_status = BoxStatus(toolbox_id=toolbox_id)
                session.add(box_status)
            
            box_status.last_check_time = datetime.utcnow()
            box_status.last_check_user = user.id
            box_status.is_complete = all_present
            
            await session.commit()
        
        # Формуємо звіт
        total = len(results)
        present_count = sum(1 for r in results if r["present"])
        missing_count = total - present_count
        
        # Отримуємо назву ящика
        toolbox_name = toolbox.name if toolbox else "Невідомий ящик"
        
        result_text = f"📋 **Результати перевірки ящика \"{toolbox_name}\"**\n"
        result_text += "━" * 30 + "\n\n"
        result_text += f"📊 **Загальна статистика:**\n"
        result_text += f"│   ✅ Присутні: {present_count}/{total}\n"
        result_text += f"│   ❌ Відсутні: {missing_count}/{total}\n"
        
        if missing_count > 0:
            result_text += f"\n⚠️ **Список відсутніх інструментів:**\n"
            for r in results:
                if not r["present"]:
                    result_text += f"│   • {r['tool']}\n"
                    if r.get("comment"):
                        result_text += f"│     📝 {r['comment']}\n"
        
        result_text += f"\n✅ Перевірку завершено!"
        
        await callback.message.answer(
            result_text,
            parse_mode="Markdown",
            reply_markup=main_menu_by_role(active_role.get(callback.from_user.id, "operator"))
        )
        
    except Exception as e:
        logger.error(f"Помилка при збереженні перевірки: {e}")
        await callback.message.answer(f"❌ Сталася помилка при збереженні: {str(e)}")
    finally:
        await state.clear()

@router.message(CheckState.photo)
async def save_photo_and_check(message: Message, state: FSMContext):
    photo_path = None
    if message.photo:
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        os.makedirs("media", exist_ok=True)
        photo_path = f"media/{file.file_id}.jpg"
        await message.bot.download_file(file.file_path, photo_path)
    
    data = await state.get_data()
    results = data.get("results", [])
    toolbox_id = data.get("toolbox_id")
    
    if not results:
        await message.answer("❌ Немає даних про перевірку. Спробуйте ще раз.")
        await state.clear()
        return
    
    try:
        async with async_session() as session:
            # Отримуємо користувача
            user_result = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                # Якщо користувача немає в БД, створюємо нового
                user = User(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username or "",
                    full_name=message.from_user.full_name or "Користувач",
                    role="operator"
                )
                session.add(user)
                await session.commit()
                logger.info(f"Створено нового користувача: {user.telegram_id}")
            
            # Отримуємо ящик
            toolbox = await session.get(Toolbox, toolbox_id)
            if not toolbox:
                await message.answer("❌ Ящик не знайдено")
                await state.clear()
                return
            
            # Зберігаємо результати
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
            
            # Оновлюємо статус ящика
            box_status_result = await session.execute(
                select(BoxStatus).where(BoxStatus.toolbox_id == toolbox_id)
            )
            box_status = box_status_result.scalar_one_or_none()
            if not box_status:
                box_status = BoxStatus(toolbox_id=toolbox_id)
                session.add(box_status)
            
            box_status.last_check_time = datetime.utcnow()
            box_status.last_check_user = user.id
            box_status.is_complete = all_present
            
            await session.commit()
        
        # Формуємо звіт
        total = len(results)
        present_count = sum(1 for r in results if r["present"])
        missing_count = total - present_count
        
        toolbox_name = toolbox.name if toolbox else "Невідомий ящик"
        
        result_text = f"📋 **Результати перевірки ящика \"{toolbox_name}\"**\n"
        result_text += "━" * 30 + "\n\n"
        result_text += f"📊 **Загальна статистика:**\n"
        result_text += f"│   ✅ Присутні: {present_count}/{total}\n"
        result_text += f"│   ❌ Відсутні: {missing_count}/{total}\n"
        
        if missing_count > 0:
            result_text += f"\n⚠️ **Список відсутніх інструментів:**\n"
            for r in results:
                if not r["present"]:
                    result_text += f"│   • {r['tool']}\n"
                    if r.get("comment"):
                        result_text += f"│     📝 {r['comment']}\n"
        
        result_text += f"\n✅ Перевірку завершено!"
        if photo_path:
            result_text += f"\n📸 Фото збережено!"
        
        await message.answer(
            result_text,
            parse_mode="Markdown",
            reply_markup=main_menu_by_role(active_role.get(message.from_user.id, "operator"))
        )
        
    except Exception as e:
        logger.error(f"Помилка при збереженні перевірки: {e}")
        await message.answer(f"❌ Сталася помилка при збереженні: {str(e)}")
    finally:
        await state.clear()

@router.message(F.text == "📜 Історія моїх перевірок")
async def my_history(message: Message):
    async with async_session() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            # Якщо користувача немає в БД, створюємо нового
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username or "",
                full_name=message.from_user.full_name or "Користувач",
                role="operator"
            )
            session.add(user)
            await session.commit()
        
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
            toolbox_name = toolbox.name if toolbox else "Невідомий ящик"
            text += f"📦 **{toolbox_name}**\n"
            text += f"   🔧 {ch.tool_name}: {'✅' if ch.is_present else '❌'}\n"
            text += f"   🕐 {ch.timestamp.strftime('%d.%m.%Y %H:%M:%S')}\n"
            if ch.comment:
                text += f"   📝 {ch.comment}\n"
            text += "   ---\n\n"
        
        await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "📸 Фото інструментів")
async def view_tool_photos(message: Message):
    async with async_session() as session:
        toolboxes = await session.execute(select(Toolbox))
        toolboxes = toolboxes.scalars().all()
        if not toolboxes:
            await message.answer("❌ Немає створених ящиків.")
            return
        await message.answer("Оберіть ящик:", reply_markup=toolboxes_list_kb(toolboxes, "photos"))

@router.callback_query(F.data.startswith("photos_"))
async def show_tools_for_photo(callback: CallbackQuery):
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
            await callback.message.answer(f"❌ У ящику {toolbox.name} немає інструментів")
            await callback.answer()
            return
        
        buttons = [[InlineKeyboardButton(text=f"📷 {tool}", callback_data=f"view_photo_{toolbox_id}_{tool}")] for tool in tools]
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.answer(f"📸 Оберіть інструмент у ящику {toolbox.name}:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("view_photo_"))
async def show_photo(callback: CallbackQuery):
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("Помилка: невірний формат даних")
        return
    
    toolbox_id = safe_int(parts[1])
    tool_name = "_".join(parts[2:]) if len(parts) > 2 else parts[2]
    
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
