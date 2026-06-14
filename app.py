from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if data and "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            
            if text == "/start":
                reply = "✅ Бот для контролю інструментів працює на Render!"
            else:
                reply = f"Ви написали: {text}"
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": reply})
        return "OK", 200
    except Exception as e:
        print(f"Помилка: {e}")
        return "Error", 500

@app.route('/')
def index():
    return "Toolbox Bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
