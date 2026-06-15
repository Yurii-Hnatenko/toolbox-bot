import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base
import urllib.parse

# Отримуємо URL бази даних зі змінних середовища Render
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL:
    # Конвертуємо postgres:// в postgresql+asyncpg://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        # Витягуємо компоненти для правильного форматування
        parts = DATABASE_URL.replace("postgresql://", "").split("@")
        if len(parts) == 2:
            user_pass = parts[0]
            host_db = parts[1]
            DATABASE_URL = f"postgresql+asyncpg://{user_pass}@{host_db}"
else:
    # Для локального тестування
    DATABASE_URL = "sqlite+aiosqlite:///toolbox.db"

print(f"📁 Підключення до бази даних")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Таблиці бази даних створено")
