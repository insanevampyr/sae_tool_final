import subprocess
import json

def fetch_tweets(query, max_results=5):
    command = [
        "snscrape", "--jsonl",
        "twitter-search", query
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split("\n")
        tweets = [json.loads(line) for line in lines[:max_results]]
        return tweets
    except subprocess.CalledProcessError as e:
        print("❌ Scraping failed:", e.stderr)
        return []

if __name__ == "__main__":
    tweets = fetch_tweets("bitcoin since:2024-05-01", 5)

    if not tweets:
        print("⚠️ No tweets returned.")
    else:
        for tweet in tweets:
            print(f"{tweet['date']} - {tweet['content']}")
