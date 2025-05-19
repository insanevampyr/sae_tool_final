#!/usr/bin/env python3
# fetch_prices.py

import requests
import pandas as pd
from typing import List

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

def fetch_prices(coins: List[str], vs_currency: str = "usd", timeout: int = 10) -> pd.DataFrame:
    """
    Fetch current prices for a list of coins from CoinGecko.
    coins: display names matching your app (e.g. "Bitcoin", "Ethereum").
    Returns a DataFrame with columns ['Coin','PriceUSD'].
    """
    # map display names to CoinGecko IDs
    id_map = {
        "Bitcoin":  "bitcoin",
        "Ethereum": "ethereum",
        "Solana":   "solana",
        "Dogecoin": "dogecoin",
    }
    # build the request
    ids = ",".join(id_map[c] for c in coins)
    params = {"ids": ids, "vs_currencies": vs_currency}
    resp = requests.get(COINGECKO_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()  # e.g. {"bitcoin":{"usd":10234}, ...}

    rows = []
    for coin in coins:
        cg_id = id_map[coin]
        price = data.get(cg_id, {}).get(vs_currency)
        rows.append({"Coin": coin, "PriceUSD": price})

    return pd.DataFrame(rows)

if __name__ == "__main__":
    # quick test
    df = fetch_prices(["Bitcoin","Ethereum","Solana","Dogecoin"])
    print(df)
