# analyze_sentiment.py

import pandas as pd
from datetime import datetime, timezone
from textblob import TextBlob

from rss_fetch import fetch_rss_items
from reddit_fetch import fetch_reddit_posts

HIST_CSV = "sentiment_history.csv"

def analyze_sentiment(text):
    return TextBlob(text).sentiment.polarity

def get_latest_sentiment():
    coins = ["Bitcoin","Ethereum","Solana","Dogecoin"]
    reddit = fetch_reddit_posts(coins)
    rss    = fetch_rss_items(coins)
    df = pd.DataFrame(reddit + rss)

    # parse ISO8601 with offset
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    newest = df.sort_values("Timestamp", ascending=False).iloc[0]

    sent   = analyze_sentiment(newest["Content"])
    action = "Hold" if abs(sent)<0.2 else ("Buy" if sent>0 else "Sell")
    price  = newest.get("PriceUSD", None)

    return {
        "Timestamp":       newest["Timestamp"].isoformat(),
        "Coin":            newest["Coin"],
        "Source":          newest["Source"],
        "Sentiment":       round(sent, 3),
        "PriceUSD":        price,
        "SuggestedAction": action
    }
