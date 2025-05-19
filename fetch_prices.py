import time
import requests
import pandas as pd

def fetch_prices(coins, timeout=10, retries=3):
    """
    Fetch current USD prices for the given list of CoinGecko coin IDs.
    Retries once on 429 with exponential backoff.
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join([c.lower() for c in coins]),
        "vs_currencies": "usd",
    }

    for attempt in range(retries):
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code == 429:  # Too Many Requests
            backoff = 1 * (2 ** attempt)
            time.sleep(backoff)
            continue
        resp.raise_for_status()
        break
    else:
        # If we exhausted retries, this will raise on the last attempt
        resp.raise_for_status()

    data = resp.json()
    rows = []
    for c in coins:
        usd = data.get(c.lower(), {}).get("usd")
        rows.append({"Coin": c, "PriceUSD": usd})
    return pd.DataFrame(rows)

if __name__ == "__main__":
    # Quick CLI check
    coins = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
    df = fetch_prices(coins)
    print(df.to_string(index=False))
