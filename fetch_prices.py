# fetch_prices.py
import requests

def fetch_prices():
    coins = {
        "Bitcoin": "bitcoin",
        "Ethereum": "ethereum",
        "Solana": "solana",
        "Dogecoin": "dogecoin"
    }
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(coins.values()),
        "vs_currencies": "usd"
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        prices_raw = response.json()
        return {coin: prices_raw.get(slug, {}).get("usd", 0.0) for coin, slug in coins.items()}
    else:
        return {coin: 0.0 for coin in coins}
