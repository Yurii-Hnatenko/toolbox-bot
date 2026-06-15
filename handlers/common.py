from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from database import SessionLocal
from models import User
from keyboards import main_menu_by_role
from config import ADMIN_IDS
import logging

logger = logging.getLogger(__name__)
router = Router()

# Глобальний словник для зберігання активної ролі
active_role = {}

@router.message(Command("start"))
async def cmd_start(message: Message):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        
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
            db.add(user)
            db.commit()
        else:
            if message.from_user.id in ADMIN_IDS:
                need_update = False
                for r in ["admin", "mechanic", "operator"]:
                    if not user.has_role(r):
                        user.add_role(r)
                        need_update = True
                if need_update:
                    db.commit()
                    logger.info(f"Оновлено ролі для адміна {message.from_user.id}: {user.role_list}")
        
        if message.from_user.id not in active_role:
            active_role[message.from_user.id] = user.primary_role
        
        current_active = active_role.get(message.from_user.id)
        if current_active not in user.role_list:
            active_role[message.from_user.id] = user.primary_role
        
        await message.answer(
            f"👋 Вітаю, {message.from_user.full_name}!\n\n"
            f"📋 Ваші ролі: {', '.join(user.role_list)}\n"
            f"⭐ Активна роль: {active_role.get(message.from_user.id, user.primary_role).capitalize()}\n\n"
            f"Оберіть дію з меню:",
            reply_markup=main_menu_by_role(active_role.get(message.from_user.id, user.primary_role))
        )
    except Exception as e:
        logger.error(f"Помилка в cmd_start: {e}")
        await message.answer("❌ Сталася помилка при реєстрації. Спробуйте ще раз.")
    finally:
        db.close()

@router.message(F.text == "ℹ️ Інформація")
async def info(message: Message):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        
        if not user:
            await message.answer("❌ Користувача не знайдено. Надішліть /start")
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
    except Exception as e:
        logger.error(f"Помилка в info: {e}")
        await message.answer("❌ Сталася помилка при отриманні інформації.")
    finally:
        db.close()

@router.message(F.text == "🔙 На головну")
async def back_to_main(message: Message):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        
        if not user:
            await message.answer("❌ Користувача не знайдено. Надішліть /start")
            return
        
        current_role = active_role.get(message.from_user.id, user.primary_role)
        
        await message.answer(
            "🔙 Повернення до головного меню:",
            reply_markup=main_menu_by_role(current_role)
        )
    except Exception as e:
        logger.error(f"Помилка в back_to_main: {e}")
        await message.answer("❌ Сталася помилка. Спробуйте ще раз.")
    finally:
        db.close()
