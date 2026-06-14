import os
import sys
import asyncio
from flask import Flask, request
import logging
import requests
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.getcwd())

app = Flask(__name__)

# Отримуємо токен зі змінних середовища
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Ініціалізація бази даних
try:
    from database import init_db
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_db())
    logger.info("✅ База даних ініціалізована")
except Exception as e:
    logger.error(f"❌ Помилка ініціалізації бази: {e}")

# Імпортуємо бота (повна версія)
try:
    from main import bot, dp
    from aiogram.types import Update
    logger.info("✅ Бот успішно імпортований")
except Exception as e:
    logger.error(f"❌ Помилка імпорту бота: {e}")

# Створюємо окремий цикл подій для обробки асинхронних задач
event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(event_loop)

def run_async(coro):
    """Запускає асинхронну функцію в нашому циклі подій"""
    future = asyncio.run_coroutine_threadsafe(coro, event_loop)
    return future.result(timeout=30)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logger.info("Отримано webhook запит")
        
        if not data:
            return 'No data', 400
        
        # Обробляємо повідомлення через aiogram
        update = Update.model_validate(data)
        run_async(dp.feed_update(bot, update))
        
        return 'OK', 200
    except Exception as e:
        logger.error(f"Помилка webhook: {e}")
        return 'Error', 500

@app.route('/')
def index():
    return 'Toolbox Bot is running!', 200

# Запускаємо цикл подій у фоновому потоці
def start_event_loop():
    event_loop.run_forever()
threading.Thread(target=start_event_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
