#!/usr/bin/env python3
from pycoingecko import CoinGeckoAPI
import pandas as pd

g = CoinGeckoAPI()

ID_MAP = {
    "bitcoin":  "bitcoin",
    "ethereum": "ethereum",
    "solana":   "solana",
    "dogecoin": "dogecoin",
}

def get_hourly_history(coin: str, days: int = 7) -> pd.DataFrame:
    cg_id = ID_MAP[coin.lower()]
    data = g.get_coin_market_chart_by_id(id=cg_id, vs_currency="usd", days=days)
    prices = data["prices"]  # list of [timestamp_ms, price]
    df = pd.DataFrame(prices, columns=["ts_ms", "PriceUSD"])
    df["Timestamp"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True).dt.tz_convert(None)
    df["Coin"] = coin.capitalize()   # Ensures "Bitcoin", "Ethereum", etc.
    return df[["Timestamp", "Coin", "PriceUSD"]]

if __name__ == "__main__":
    dfs = []
    for coin in ["bitcoin", "ethereum", "solana", "dogecoin"]:
        dfs.append(get_hourly_history(coin, days=7))
    df = pd.concat(dfs)
    df.to_csv("btc_history.csv", index=False)
    print("✅ Wrote btc_history.csv")
