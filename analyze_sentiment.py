# analyze_sentiment.py

import os
import json
import pandas as pd
from datetime import datetime, timezone

from reddit_fetch import fetch_reddit_posts
from rss_fetch    import fetch_rss_items
from textblob     import TextBlob

HIST_CSV = "sentiment_history.csv"

def analyze_sentiment(text):
    """Return polarity float between -1 and +1."""
    return TextBlob(text).sentiment.polarity

def get_latest_sentiment():
    """Fetch new posts/articles, compute sentiment, and return a dict ready to append."""
    coins = ["Bitcoin","Ethereum","Solana","Dogecoin"]
    # 1) gather raw posts (you already have these modules)
    reddit = fetch_reddit_posts(coins)
    rss    = fetch_rss_items(coins)
    all_items = reddit + rss

    # 2) build DataFrame
    df = pd.DataFrame(all_items)
    # ensure Timestamp column is parsed properly (ISO8601 with offset)
    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"],
        utc=True,
        errors="coerce",    # drop any malformed
    )

    # pick the single newest row
    newest = df.sort_values("Timestamp", ascending=False).iloc[0]

    # 3) compute sentiment & suggested action
    sent = analyze_sentiment(newest["Content"])
    action = "Hold" if abs(sent)<0.2 else ("Buy" if sent>0 else "Sell")
    price = newest.get("PriceUSD", None)

    return {
        "Timestamp":       newest["Timestamp"].isoformat(),
        "Coin":            newest["Coin"],
        "Source":          newest["Source"],
        "Sentiment":       round(sent, 3),
        "PriceUSD":        price,
        "SuggestedAction": action
    }
