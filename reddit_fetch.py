# reddit_fetch.py
import os
from dotenv import load_dotenv
import praw
from analyze_sentiment import analyze_sentiment

# load from .env (in production your CI / Streamlit secrets will also populate os.environ)
load_dotenv()

def fetch_reddit_posts(subreddit_name, keyword, limit=5):
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=f"cryptoSentimentApp by /u/{os.getenv('REDDIT_USERNAME')}",
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
    )

    posts = []
    for submission in reddit.subreddit(subreddit_name).search(keyword, limit=limit):
        sentiment = analyze_sentiment(submission.title)
        posts.append({
            "text": submission.title,
            "sentiment": sentiment,
            "url": submission.url
        })
    return posts
