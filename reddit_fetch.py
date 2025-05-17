import os
from dotenv import load_dotenv
import praw

# Load .env before reading credentials
load_dotenv()

# Instantiate PRAW client with env vars
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT"),
)

def fetch_reddit_posts(coins, limit=100):
    """
    Fetch latest submissions from r/CryptoCurrency for each coin keyword.
    Returns a list of dicts: { "timestamp": iso, "coin": coin, "text": title+body }.
    """
    posts = []
    for coin in coins:
        for submission in reddit.subreddit("CryptoCurrency").search(
            query=coin, sort="new", limit=limit
        ):
            posts.append({
                "timestamp": datetime.fromtimestamp(
                    submission.created_utc, tz=timezone.utc
                ).isoformat(),
                "coin": coin,
                "text": submission.title + "\n" + submission.selftext
            })
    return posts
