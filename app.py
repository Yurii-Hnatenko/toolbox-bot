import os
import sys
import asyncio
from flask import Flask, request
from aiogram.types import Update

# Додаємо шлях до проекту
sys.path.insert(0, os.getcwd())

app = Flask(__name__)

# Імпортуємо бота
from main import bot, dp
from config import BOT_TOKEN

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if data:
            update = Update.model_validate(data)
            asyncio.run(dp.feed_update(bot, update))
            return 'OK', 200
        return 'No data', 400
    except Exception as e:
        print(f"Помилка вебхука: {e}")
        return 'Error', 500

@app.route('/')
def index():
    return 'Toolbox Bot is running!', 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
