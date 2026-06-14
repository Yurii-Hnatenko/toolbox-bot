import os
import sys
import asyncio
from flask import Flask, request
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.getcwd())

app = Flask(__name__)

# Ініціалізація бази даних при старті
from database import init_db
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_db())
print("✅ База даних ініціалізована")

from main import bot, dp
from aiogram.types import Update

# Створюємо єдиний цикл подій для всіх запитів
event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(event_loop)

def run_event_loop():
    event_loop.run_forever()
threading.Thread(target=run_event_loop, daemon=True).start()

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if data:
            update = Update.model_validate(data)
            future = asyncio.run_coroutine_threadsafe(dp.feed_update(bot, update), event_loop)
            future.result(timeout=30)
            return 'OK', 200
        return 'No data', 400
    except Exception as e:
        logger.error(f"Помилка: {e}")
        return 'Error', 500

@app.route('/')
def index():
    return 'Toolbox Bot is running!', 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
