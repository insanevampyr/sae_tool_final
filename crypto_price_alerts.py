# crypto_price_alerts.py

import requests
import time
from send_telegram import send_telegram_message

# CoinGecko API endpoints
API_URL = "https://api.coingecko.com/api/v3/simple/price"

# Watched coins and thresholds
WATCHED_COINS = {
    "bitcoin": {"symbol": "BTC", "threshold_up": 3, "threshold_down": -3},
    "ethereum": {"symbol": "ETH", "threshold_up": 3, "threshold_down": -3},
    "solana": {"symbol": "SOL", "threshold_up": 5, "threshold_down": -5},
    "dogecoin": {"symbol": "DOGE", "threshold_up": 7, "threshold_down": -7}
}

# Cache for storing previous prices
last_prices = {}

def fetch_prices():
    ids = ','.join(WATCHED_COINS.keys())
    params = {
        'ids': ids,
        'vs_currencies': 'usd'
    }
    response = requests.get(API_URL, params=params)
    return response.json()

def check_price_changes():
    global last_prices
    current_prices = fetch_prices()
    alerts = []

    for coin, data in WATCHED_COINS.items():
        symbol = data['symbol']
        new_price = current_prices.get(coin, {}).get('usd')
        if new_price is None:
            continue

        old_price = last_prices.get(coin)
        if old_price:
            change_percent = ((new_price - old_price) / old_price) * 100

            if change_percent >= data['threshold_up']:
                alerts.append(f"📈 {symbol} price increased by {change_percent:.2f}%: ${old_price:.2f} → ${new_price:.2f}")
            elif change_percent <= data['threshold_down']:
                alerts.append(f"📉 {symbol} price dropped by {change_percent:.2f}%: ${old_price:.2f} → ${new_price:.2f}")

        last_prices[coin] = new_price

    if alerts:
        for alert in alerts:
            send_telegram_message(alert)

if __name__ == "__main__":
    check_price_changes()
