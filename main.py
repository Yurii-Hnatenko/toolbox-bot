import asyncio
import os
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
from handlers import common, operator, mechanic, admin, role_switch

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Ця функція виконується ПЕРЕД стартом бота
async def on_startup():
    os.makedirs("media", exist_ok=True)
    await init_db()
    print("✅ База даних ініціалізована")

# Реєструємо startup handler
dp.startup.register(on_startup)

# Реєструємо всі handlers
dp.include_router(common.router)
dp.include_router(operator.router)
dp.include_router(mechanic.router)
dp.include_router(admin.router)
dp.include_router(role_switch.router)

# Для вебхука
async def process_update(update_dict: dict):
    from aiogram.types import Update
    update = Update.model_validate(update_dict)
    await dp.feed_update(bot, update)

# Для локального тестування
async def main():
    await on_startup()
    print("✅ Бот запущено в режимі polling")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
