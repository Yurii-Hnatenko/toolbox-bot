import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base

# Отримуємо URL бази даних зі змінних середовища Render
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL:
    # Конвертуємо для синхронного використання
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print(f"✅ Підключення до PostgreSQL (синхронне)")
else:
    # Для локального тестування (SQLite)
    DATABASE_URL = "sqlite:///toolbox.db"
    print(f"⚠️ Локальне підключення до SQLite")

# Створюємо двигун бази даних
engine = create_engine(
    DATABASE_URL, 
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

# Створюємо фабрику сесій
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Повертає сесію бази даних"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Ініціалізує базу даних, створює всі таблиці"""
    Base.metadata.create_all(bind=engine)
    print("✅ Таблиці бази даних створено")
