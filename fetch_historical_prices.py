#!/usr/bin/env python3
# fetch_historical_prices.py

from pycoingecko import CoinGeckoAPI
import pandas as pd

# instantiate client
g = CoinGeckoAPI()

# map our coin names to CoinGecko IDs
ID_MAP = {
    "Bitcoin":  "bitcoin",
    "Ethereum": "ethereum",
    "Solana":   "solana",
    "Dogecoin": "dogecoin",
}

def get_hourly_history(coin: str, days: int = 7) -> pd.DataFrame:
    """
    Fetch last <days> days of hourly price data for a coin.
    Returns DataFrame with columns ['Timestamp','PriceUSD'].
    """
    cg_id = ID_MAP[coin]
    # do NOT specify interval; default hourly when days between 2–90
    data = g.get_coin_market_chart_by_id(cg_id, vs_currency="usd", days=days)
    prices = data["prices"]    # list of [timestamp_ms, price]

    df = pd.DataFrame(prices, columns=["ts_ms","PriceUSD"])
    df["Timestamp"] = pd.to_datetime(df["ts_ms"], unit="ms")
    return df[["Timestamp","PriceUSD"]]

if __name__ == "__main__":
    # example: write Bitcoin history
    df = get_hourly_history("Bitcoin", days=7)
    df.to_csv("btc_history.csv", index=False)
    print("✅ Wrote btc_history.csv")
