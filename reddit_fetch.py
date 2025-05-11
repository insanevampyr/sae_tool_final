import praw
import os
from dotenv import load_dotenv
from analyze_sentiment import analyze_sentiment

# Load .env variables
load_dotenv()

def fetch_reddit_posts(subreddit_name, keyword, limit=5):
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent="cryptoSentimentApp by /u/" + os.getenv("REDDIT_USERNAME"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD")
    )

    subreddit = reddit.subreddit(subreddit_name)
    posts = []

    for submission in subreddit.search(keyword, limit=limit):
        sentiment = analyze_sentiment(submission.title)
        posts.append({
            "text": submission.title,
            "sentiment": sentiment,
            "url": submission.url
        })

    return posts
