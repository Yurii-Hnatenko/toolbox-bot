import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Update  # Додано імпорт Update
from config import BOT_TOKEN
from database import init_db
from handlers import common, operator, mechanic, admin, role_switch

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def on_startup():
    os.makedirs("media", exist_ok=True)
    await init_db()
    print("✅ База даних ініціалізована")

dp.startup.register(on_startup)

# Реєструємо всі handlers
dp.include_router(common.router)
dp.include_router(operator.router)
dp.include_router(mechanic.router)
dp.include_router(admin.router)
dp.include_router(role_switch.router)

async def main():
    print("✅ Бот запущено!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
