import praw
from analyze_sentiment import analyze_sentiment

def fetch_reddit_posts(subreddit_name, keyword, limit=5):
    reddit = praw.Reddit(
        client_id="Inj8JZXelE1yOPEi6Qi03Q",
        client_secret="T6od45R8ysAresMsZBTleNhJKkPYjw",
        user_agent="cryptoSentimentApp by /u/Either-Scientist-626",
        username="Either-Scientist-626",
        password="Freepot1!"
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
