# reddit_fetch.py

import os
import praw
from datetime import datetime

# no analyze_sentiment import here—just fetch raw posts!

REDDIT_CLIENT = os.getenv("REDDIT_CLIENT_ID")
REDDIT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT    = "AlphaPulse/1.0"

def fetch_reddit_posts(coins):
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT,
        client_secret=REDDIT_SECRET,
        user_agent=USER_AGENT
    )

    items = []
    for coin in coins:
        subreddit = reddit.subreddit(coin.lower())
        for post in subreddit.new(limit=10):
            items.append({
                "Timestamp":  datetime.fromtimestamp(post.created_utc, tz=datetime.timezone.utc).isoformat(),
                "Coin":       coin,
                "Source":     "reddit",
                "Content":    post.title + "\n\n" + post.selftext,
                # PriceUSD not known here
            })
    return items
