import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
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
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    print(f"✅ Підключення до PostgreSQL")
else:
    # Для локального тестування (SQLite)
    DATABASE_URL = "sqlite+aiosqlite:///toolbox.db"
    print(f"⚠️ Локальне підключення до SQLite")

# Створюємо двигун бази даних з налаштуваннями для уникнення конфліктів
engine = create_async_engine(
    DATABASE_URL, 
    echo=False,
    pool_size=5,           # Розмір пулу з'єднань
    max_overflow=10,       # Максимальна кількість додаткових з'єднань
    pool_pre_ping=True,    # Перевірка з'єднання перед використанням
    pool_recycle=3600      # Перепідключення через 1 годину
)

# Створюємо фабрику сесій
async_session = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def init_db():
    """Ініціалізує базу даних, створює всі таблиці"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Таблиці бази даних створено")

async def get_session():
    """Повертає нову сесію для запиту"""
    async with async_session() as session:
        yield session
