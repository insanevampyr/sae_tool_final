# send_telegram.py

import requests

# Replace with your actual bot token and chat ID
BOT_TOKEN = "7767646415:AAF9rItYub_OSQU9ZsbGEhtxYMCSZtBZqHo"
CHAT_ID = "535297117"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("✅ Telegram alert sent.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send alert: {e}")
