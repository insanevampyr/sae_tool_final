#!/usr/bin/env python3
# fetch_historical_prices.py

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
    """
    Fetch the last <days> days of hourly price data for `coin`.
    Returns a DataFrame with naive UTC Timestamp and PriceUSD.
    """
    cg_id = ID_MAP[coin.lower()]
    data = g.get_coin_market_chart_by_id(
        id=cg_id,
        vs_currency="usd",
        days=days
    )
    prices = data["prices"]  # list of [timestamp_ms, price]

    df = pd.DataFrame(prices, columns=["ts_ms", "PriceUSD"])
    # UTC timestamp (tz-aware) → drop tz → naive UTC
    df["Timestamp"] = (
        pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
          .dt.tz_convert(None)
    )
    return df[["Timestamp", "PriceUSD"]]

if __name__ == "__main__":
    df_btc = get_hourly_history("bitcoin", days=7)
    df_btc.to_csv("btc_history.csv", index=False)
    print("✅ Wrote btc_history.csv")
