import tweepy

# 🔐 REPLACE THESE with your actual keys from the developer portal
bearer_token = "AAAAAAAAAAAAAAAAAAAAAP%2By1AEAAAAAYSYmG370GZXVK6pgbF9tQzS27h4%3D0g87PoR7dXMGRuOA3D8WnD9VUTOQQaAq9kAPFfwd0eln72g1zZ"

client = tweepy.Client(bearer_token=bearer_token)

def fetch_tweets(query, max_results=10):
    response = client.search_recent_tweets(
        query=query,
        tweet_fields=["created_at", "text"],
        max_results=max_results
    )

    tweets = response.data or []
    return tweets

if __name__ == "__main__":
    tweets = fetch_tweets("bitcoin lang:en", 10)

    if not tweets:
        print("⚠️ No tweets found.")
    else:
        for tweet in tweets:
            print(f"{tweet.created_at} - {tweet.text}")
