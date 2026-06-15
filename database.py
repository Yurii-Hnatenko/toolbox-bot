import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base

# Отримуємо URL бази даних зі змінних середовища Render
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Конвертуємо postgres:// в postgresql+asyncpg://
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    else:
        DATABASE_URL = "postgresql+asyncpg://" + DATABASE_URL.replace("postgresql://", "")

# Для локального тестування (SQLite)
if not DATABASE_URL:
    DATABASE_URL = "sqlite+aiosqlite:///toolbox.db"

print(f"📁 Підключення до бази даних")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Таблиці бази даних створено")
