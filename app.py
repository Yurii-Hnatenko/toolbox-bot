import os
import sys
import asyncio
from flask import Flask, request
import logging
import threading
from functools import wraps
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.getcwd())

app = Flask(__name__)

# Ініціалізація бази даних
try:
    from database import init_db
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_db())
    logger.info("✅ База даних ініціалізована")
except Exception as e:
    logger.error(f"❌ Помилка ініціалізації бази: {e}")

# Імпортуємо бота
try:
    from main import bot, dp
    from aiogram.types import Update
    logger.info("✅ Бот успішно імпортований")
except Exception as e:
    logger.error(f"❌ Помилка імпорту бота: {e}")

# Створюємо окремий цикл подій
event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(event_loop)

def run_async(coro, retries=3, delay=1):
    """Запускає асинхронну функцію з повторними спробами при помилках"""
    for attempt in range(retries):
        try:
            future = asyncio.run_coroutine_threadsafe(coro, event_loop)
            return future.result(timeout=30)
        except Exception as e:
            logger.error(f"Спроба {attempt + 1} невдала: {e}")
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                raise

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logger.info("Отримано webhook запит")
        
        if not data:
            return 'No data', 400
        
        update = Update.model_validate(data)
        run_async(dp.feed_update(bot, update))
        
        return 'OK', 200
    except Exception as e:
        logger.error(f"Помилка webhook: {e}")
        return 'Error', 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint для Render"""
    return 'OK', 200

@app.route('/')
def index():
    return 'Toolbox Bot is running!', 200

def start_event_loop():
    event_loop.run_forever()
threading.Thread(target=start_event_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
