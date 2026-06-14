from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from database import async_session
from models import User
from keyboards import main_menu_by_role
from config import ADMIN_IDS
from sqlalchemy import select

router = Router()

# Словник для зберігання активної ролі
active_role = {}

# Версія бота (змінюй при оновленнях)
BOT_VERSION = "2.0.0"

@router.message(Command("start"))
async def cmd_start(message: Message):
    async with async_session() as session:
        # Отримуємо або створюємо користувача
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        if not user:
            # Новий користувач
            if message.from_user.id in ADMIN_IDS:
                role = "admin,mechanic,operator"
            else:
                role = "operator"
            
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username or "",
                full_name=message.from_user.full_name,
                role=role,
                last_version=BOT_VERSION
            )
            session.add(user)
            await session.commit()
            
            # Встановлюємо активну роль
            active_role[message.from_user.id] = user.primary_role
            
            await message.answer(
                f"👋 Вітаю, {message.from_user.full_name}!\n"
                f"Ваші ролі: {', '.join(user.role_list)}\n"
                f"Активна роль: {user.primary_role}\n\n"
                f"Оберіть дію з меню:",
                reply_markup=main_menu_by_role(user.primary_role)
            )
        else:
            # Перевіряємо версію бота (оновлення)
            is_updated = False
            if not hasattr(user, 'last_version') or user.last_version != BOT_VERSION:
                user.last_version = BOT_VERSION
                await session.commit()
                is_updated = True
            
            # Встановлюємо активну роль
            if message.from_user.id not in active_role:
                active_role[message.from_user.id] = user.primary_role
            
            # Формуємо повідомлення
            current_active_role = active_role.get(message.from_user.id, user.primary_role)
            
            if is_updated:
                await message.answer(
                    f"👋 Вітаю, {message.from_user.full_name}!\n"
                    f"✨ **Бот оновлено до версії {BOT_VERSION}!** ✨\n\n"
                    f"Ваші ролі: {', '.join(user.role_list)}\n"
                    f"Активна роль: {current_active_role}\n\n"
                    f"📌 Додано нові функції:\n"
                    f"• Оператор: фото інструментів\n"
                    f"• Механік: розширений звіт\n"
                    f"• Адмін: розсилка оновлень\n\n"
                    f"Оберіть дію з меню:",
                    reply_markup=main_menu_by_role(current_active_role)
                )
            else:
                await message.answer(
                    f"👋 З поверненням, {message.from_user.full_name}!\n"
                    f"Ваші ролі: {', '.join(user.role_list)}\n"
                    f"Активна роль: {current_active_role}\n\n"
                    f"Оберіть дію з меню:",
                    reply_markup=main_menu_by_role(current_active_role)
                )


@router.message(F.text == "ℹ️ Інформація")
async def info(message: Message):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one()
        current_active_role = active_role.get(message.from_user.id, user.primary_role)
        
        await message.answer(
            f"👤 **Інформація про користувача**\n\n"
            f"📛 Ім'я: {user.full_name}\n"
            f"🆔 Telegram ID: {user.telegram_id}\n"
            f"🔧 Всі ролі: {', '.join(user.role_list)}\n"
            f"⚡ Активна роль: {current_active_role}\n"
            f"📦 Версія бота: {BOT_VERSION}\n"
            f"📅 ID в системі: {user.id}",
            parse_mode="Markdown"
        )


@router.message(Command("menu"))
async def refresh_menu(message: Message):
    """Примусове оновлення меню за командою /menu"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one()
        current_active_role = active_role.get(message.from_user.id, user.primary_role)
        
        await message.answer(
            "🔄 **Меню оновлено!**\n"
            "Тепер доступні актуальні функції.",
            reply_markup=main_menu_by_role(current_active_role),
            parse_mode="Markdown"
        )


@router.message(F.text == "🔙 На головну")
async def back_to_main(message: Message):
    """Повернення до головного меню"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one()
        current_active_role = active_role.get(message.from_user.id, user.primary_role)
        
        await message.answer(
            "🔙 Повернення до головного меню:",
            reply_markup=main_menu_by_role(current_active_role)
        )


@router.message(F.text == "🔄 Оновити меню")
async def force_update_menu(message: Message):
    """Примусове оновлення меню (кнопка)"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one()
        current_active_role = active_role.get(message.from_user.id, user.primary_role)
        
        # Оновлюємо версію в БД
        if user.last_version != BOT_VERSION:
            user.last_version = BOT_VERSION
            await session.commit()
            await message.answer(
                f"✅ **Меню оновлено до версії {BOT_VERSION}!**\n\n"
                f"📌 Нові функції вже доступні.",
                reply_markup=main_menu_by_role(current_active_role),
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "✅ **Меню вже актуальне!**\n"
                f"Поточна версія: {BOT_VERSION}",
                reply_markup=main_menu_by_role(current_active_role),
                parse_mode="Markdown"
            )


async def force_user_menu_update(telegram_id: int, bot):
    """Примусове оновлення меню користувача (використовується адміном після зміни ролей)"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one()
        
        # Скидаємо активну роль, щоб вона вибралась заново
        if telegram_id in active_role:
            # Видаляємо стару активну роль
            del active_role[telegram_id]
        
        # Встановлюємо нову активну роль (перша в списку)
        new_active_role = user.primary_role
        active_role[telegram_id] = new_active_role
        
        try:
            await bot.send_message(
                telegram_id,
                f"🔄 **Ваші ролі було змінено!**\n\n"
                f"Нові ролі: {', '.join(user.role_list)}\n"
                f"Активна роль: {new_active_role}\n\n"
                f"Меню оновлено:",
                reply_markup=main_menu_by_role(new_active_role),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Не вдалося оновити меню для {telegram_id}: {e}")