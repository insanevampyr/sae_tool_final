#!/usr/bin/env python3
# fetch_prices.py

import time
import requests
import pandas as pd
from typing import List
from requests.exceptions import HTTPError

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

def fetch_prices(
    coins: List[str],
    vs_currency: str = "usd",
    timeout: int = 10,
    max_retries: int = 3,
    backoff_factor: float = 1.0
) -> pd.DataFrame:
    """
    Fetch current prices for a list of coins from CoinGecko with retry/backoff for 429s.
    Returns a DataFrame with columns ['Coin','PriceUSD'], may contain None on failure.
    """
    # map display names to CoinGecko IDs
    id_map = {
        "Bitcoin":  "bitcoin",
        "Ethereum": "ethereum",
        "Solana":   "solana",
        "Dogecoin": "dogecoin",
    }
    ids = ",".join(id_map[c] for c in coins)
    params = {"ids": ids, "vs_currencies": vs_currency}

    # Attempt request with retries on 429
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(COINGECKO_URL, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()  # e.g. {"bitcoin":{"usd":10234}, ...}
            break
        except HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            # only back‐off on rate limiting
            if code == 429 and attempt < max_retries:
                sleep_time = backoff_factor * (2 ** (attempt - 1))
                time.sleep(sleep_time)
                continue
            # on any other HTTPError or final 429, build empty data
            data = {}
            break

    rows = []
    for coin in coins:
        cg_id = id_map[coin]
        price = None
        if isinstance(data, dict):
            price = data.get(cg_id, {}).get(vs_currency)
        rows.append({"Coin": coin, "PriceUSD": price})

    return pd.DataFrame(rows)


if __name__ == "__main__":
    # quick smoke-test
    df = fetch_prices(["Bitcoin", "Ethereum", "Solana", "Dogecoin"])
    print(df)
