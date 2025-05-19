#!/usr/bin/env python3
# fetch_historical_prices.py

from pycoingecko import CoinGeckoAPI
import pandas as pd

# Map our display names to CoinGecko IDs
ID_MAP = {
    "Bitcoin":  "bitcoin",
    "Ethereum": "ethereum",
    "Solana":   "solana",
    "Dogecoin": "dogecoin",
}

cg = CoinGeckoAPI()

def get_hourly_history(coin: str, days: int = 7) -> pd.DataFrame:
    """
    Fetch the last <days> days of hourly price data for `coin`.
    Returns a DataFrame with columns ['Timestamp','PriceUSD'].
    """
    cg_id = ID_MAP[coin]
    # Note: do NOT pass interval="hourly" here—CoinGecko will return hourly
    data = cg.get_coin_market_chart_by_id(
        id=cg_id,
        vs_currency="usd",
        days=days
    )
    prices = data["prices"]  # list of [timestamp_ms, price]
    df = pd.DataFrame(prices, columns=["ts_ms", "PriceUSD"])
    df["Timestamp"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    return df[["Timestamp", "PriceUSD"]]

if __name__ == "__main__":
    # Example usage: write Bitcoin history to CSV
    df_btc = get_hourly_history("Bitcoin", days=7)
    df_btc.to_csv("btc_history.csv", index=False)
    print("✅ Wrote btc_history.csv")
