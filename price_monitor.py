import requests
import time
from send_telegram import send_telegram_message

# Watchlist and thresholds
COINS = {
    "bitcoin": {"symbol": "BTC", "threshold_up": 2.0, "threshold_down": -2.0},
    "ethereum": {"symbol": "ETH", "threshold_up": 2.0, "threshold_down": -2.0},
    "solana": {"symbol": "SOL", "threshold_up": 3.0, "threshold_down": -3.0},
    "dogecoin": {"symbol": "DOGE", "threshold_up": 5.0, "threshold_down": -5.0},
}

# Store previous prices
previous_prices = {}

def fetch_prices():
    ids = ','.join(COINS.keys())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("❌ Price fetch failed:", e)
        return {}

def monitor_prices():
    global previous_prices
    print("📡 Monitoring prices every 60 seconds...")
    while True:
        prices = fetch_prices()
        if not prices:
            time.sleep(60)
            continue

        for coin, info in COINS.items():
            current_price = prices[coin]["usd"]
            previous_price = previous_prices.get(coin)

            if previous_price:
                change = ((current_price - previous_price) / previous_price) * 100
                change_msg = f"{info['symbol']} price: ${current_price:.2f} ({change:+.2f}%)"

                if change >= info["threshold_up"]:
                    send_telegram_message(f"🚀 {change_msg} — Price is rising!")
                elif change <= info["threshold_down"]:
                    send_telegram_message(f"🔻 {change_msg} — Price is dropping!")

            previous_prices[coin] = current_price

        time.sleep(60)  # wait before next check

if __name__ == "__main__":
    monitor_prices()
