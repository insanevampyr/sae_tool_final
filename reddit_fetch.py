# reddit_fetch.py

import os
from dotenv import load_dotenv
import praw
from datetime import datetime, timezone
from crypto_price_alerts import COINS
from textblob import TextBlob

# ─── Load your .env so os.getenv() works ─────────────────────────────────────
load_dotenv()

# ─── Initialize PRAW ────────────────────────────────────────────────────────
reddit = praw.Reddit(
    client_id     = os.getenv("REDDIT_CLIENT_ID"),
    client_secret = os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent    = os.getenv("REDDIT_USER_AGENT"),
)

def fetch_reddit_posts(coins):
    """
    Pull the latest ~50 submissions from r/CryptoCurrency,
    filter for mentions of each coin in COINS, and return
    a list of dicts: { Timestamp, Coin, Source, Text }
    """
    results = []
    for submission in reddit.subreddit("CryptoCurrency").new(limit=50):
        created = submission.created_utc
        text    = f"{submission.title}\n\n{submission.selftext}"
        for coin in coins:
            if coin.lower() in text.lower():
                results.append({
                    "Timestamp": datetime.fromtimestamp(created, tz=timezone.utc).isoformat(),
                    "Coin":      coin,
                    "Source":    "reddit",
                    "Text":      text,
                })
    return results
