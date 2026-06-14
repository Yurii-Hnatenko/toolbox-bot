import os
import sys
from flask import Flask, request
import logging
import requests
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Отримуємо токен зі змінних середовища Render
BOT_TOKEN = os.environ.get("BOT_TOKEN")

logger.info(f"Бот запускається з токеном: {BOT_TOKEN[:10]}...")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Отримуємо дані від Telegram
        data = request.get_json()
        logger.info(f"Отримано webhook запит: {data}")
        
        if not data:
            logger.warning("Немає даних у запиті")
            return 'No data', 400
        
        # Обробляємо повідомлення
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            
            logger.info(f"Повідомлення від {chat_id}: {text}")
            
            # Відповідь на /start
            if text == "/start":
                reply_text = "✅ Бот для контролю інструментів працює!\n\n"
                reply_text += "📋 Доступні команди:\n"
                reply_text += "/start - Головне меню\n"
                reply_text += "/help - Допомога"
            else:
                reply_text = f"Ви написали: {text}\n\nКоманда /start для головного меню."
            
            # Надсилаємо відповідь
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            response = requests.post(url, json={"chat_id": chat_id, "text": reply_text})
            logger.info(f"Відповідь надіслано, статус: {response.status_code}")
        
        return 'OK', 200
        
    except Exception as e:
        logger.error(f"Помилка обробки webhook: {e}")
        return f'Error: {str(e)}', 500

@app.route('/test', methods=['GET'])
def test():
    """Тестовий ендпоінт для перевірки роботи сервера"""
    return 'Server is working!', 200

@app.route('/')
def index():
    return 'Toolbox Bot is running!', 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
