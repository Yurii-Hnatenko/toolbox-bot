import os
import sys
import asyncio
from flask import Flask, request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.getcwd())

app = Flask(__name__)

from main import bot, dp
from aiogram.types import Update

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logger.info(f"Отримано оновлення: {data}")
        
        if data:
            update = Update.model_validate(data)
            asyncio.run(dp.feed_update(bot, update))
            logger.info("✅ Оновлення оброблено успішно")
            return 'OK', 200
        return 'No data', 400
    except Exception as e:
        logger.error(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        return 'Error', 500

@app.route('/')
def index():
    return 'Toolbox Bot is running!', 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
