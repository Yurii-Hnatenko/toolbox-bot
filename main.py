import asyncio
import os
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
from handlers import common, operator, mechanic, admin, role_switch

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def main():
    os.makedirs("media", exist_ok=True)
    await init_db()
    
    dp.include_router(common.router)
    dp.include_router(operator.router)
    dp.include_router(mechanic.router)
    dp.include_router(admin.router)
    dp.include_router(role_switch.router)  # Новий роутер для перемикання ролей
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Бот запущено з підтримкою множинних ролей!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())