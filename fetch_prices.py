import requests

def fetch_prices(coins):
    prices = {}
    try:
        ids = ",".join(coin.lower() for coin in coins)
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for coin in coins:
                coin_id = coin.lower()
                prices[coin] = data.get(coin_id, {}).get("usd", None)
    except Exception as e:
        print(f"Error fetching prices: {e}")
    return prices
