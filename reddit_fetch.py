# reddit_fetch.py
import os
import praw
from prawcore.exceptions import RequestException
from analyze_sentiment import analyze_sentiment

def fetch_reddit_posts(subreddit_name, keyword, limit=5):
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD")
    )

    posts = []
    try:
        subreddit = reddit.subreddit(subreddit_name)
        for submission in subreddit.search(keyword, limit=limit):
            sentiment = analyze_sentiment(submission.title)
            posts.append({
                "text": submission.title,
                "sentiment": sentiment,
                "url": submission.url
            })
    except RequestException as e:
        print(f"⚠️ Reddit fetch timeout for “{keyword}”: {e}")

    return posts
