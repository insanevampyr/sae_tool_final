import time
import requests
import pandas as pd

CACHE_FILE = "latest_prices.csv"
CACHE_TIME = 60  # seconds

def fetch_prices(coins):
    # Simple cache: reuse data if <CACHE_TIME old
    import os
    if os.path.exists(CACHE_FILE):
        mtime = os.path.getmtime(CACHE_FILE)
        if time.time() - mtime < CACHE_TIME:
            return pd.read_csv(CACHE_FILE)
    ids = ','.join([c.lower() for c in coins])
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
    resp = requests.get(url)
    if resp.status_code == 429:
        print("429 error, sleeping 60s and retrying...")
        time.sleep(60)
        resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame([
        {"Coin": c, "PriceUSD": data[c.lower()]["usd"] if c.lower() in data else None}
        for c in coins
    ])
    df.to_csv(CACHE_FILE, index=False)
    return df
