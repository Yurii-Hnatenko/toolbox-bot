import os
import sys
import asyncio
from flask import Flask, request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.getcwd())

app = Flask(__name__)

# Ініціалізуємо базу даних ПРИ СТАРТІ
from database import init_db

async def init_db_on_start():
    os.makedirs("media", exist_ok=True)
    await init_db()
    print("✅ База даних ініціалізована")

# Виконуємо ініціалізацію при запуску
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_db_on_start())

from main import bot, dp
from aiogram.types import Update

# Створюємо один цикл подій для всіх запитів
event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(event_loop)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logger.info("Отримано оновлення")
        
        if data:
            update = Update.model_validate(data)
            # Використовуємо існуючий цикл подій
            future = asyncio.run_coroutine_threadsafe(
                dp.feed_update(bot, update), 
                event_loop
            )
            future.result(timeout=30)  # Чекаємо результат до 30 секунд
            return 'OK', 200
        return 'No data', 400
    except Exception as e:
        logger.error(f"Помилка: {e}")
        return 'Error', 500

@app.route('/')
def index():
    return 'Toolbox Bot is running!', 200

# Запускаємо цикл подій у фоновому потоці
import threading
def run_event_loop():
    event_loop.run_forever()

thread = threading.Thread(target=run_event_loop, daemon=True)
thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
