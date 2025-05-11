# analyze.py
import os
import csv
from datetime import datetime
from analyze_sentiment import analyze_sentiment
from reddit_fetch import fetch_reddit_posts
from rss_fetch import fetch_rss_articles
from send_telegram import send_telegram_message
import matplotlib.pyplot as plt
import pandas as pd
import requests

coins = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
output_file = "sentiment_output.csv"
history_file = "sentiment_history.csv"
chart_file = "sentiment_chart.png"

coin_price_ids = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Solana": "solana",
    "Dogecoin": "dogecoin"
}

def get_price(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        res = requests.get(url)
        return res.json()[coin_id]["usd"]
    except:
        return None

def suggest_action(score):
    if score > 0.2:
        return "📈 Consider Buying"
    elif score < -0.2:
        return "📉 Consider Selling"
    else:
        return "🤝 Hold / Watch"

sentiment_data = []
sentiment_summary = {}

print("🧠 Fetching Reddit sentiment...\n")
for keyword in coins:
    reddit_results = fetch_reddit_posts("CryptoCurrency", keyword, 5)
    for post in reddit_results:
        sentiment = analyze_sentiment(post["text"])
        action = suggest_action(sentiment)
        sentiment_data.append({
            "Source": "Reddit",
            "Coin": keyword,
            "Text": post["text"],
            "Sentiment": sentiment,
            "SuggestedAction": action,
            "Timestamp": datetime.utcnow().isoformat(),
            "Link": post.get("url", "")
        })

print("\n📰 Fetching Crypto News sentiment...\n")
for keyword in coins:
    rss_results = fetch_rss_articles(keyword, 5)
    for post in rss_results:
        sentiment = analyze_sentiment(post["text"])
        action = suggest_action(sentiment)
        sentiment_data.append({
            "Source": "News",
            "Coin": keyword,
            "Text": post["text"],
            "Sentiment": sentiment,
            "SuggestedAction": action,
            "Timestamp": datetime.utcnow().isoformat(),
            "Link": post.get("link") or post.get("url", "")
        })

# Save latest sentiment snapshot
file_exists = os.path.isfile(output_file)

with open(output_file, "a", newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=sentiment_data[0].keys())
    if not file_exists:
        writer.writeheader()
    writer.writerows(sentiment_data)

print(f"\n✅ Sentiment results saved to {output_file}")

# Add to historical log
timestamp = datetime.utcnow().isoformat()
rows = []

for coin in coins:
    coin_data = [d for d in sentiment_data if d["Coin"] == coin]
    avg_sentiment = sum(d["Sentiment"] for d in coin_data) / len(coin_data)
    action = suggest_action(avg_sentiment)
    price = get_price(coin_price_ids[coin])
    rows.append({
        "Timestamp": timestamp,
        "Coin": coin,
        "Sentiment": avg_sentiment,
        "PriceUSD": price,
        "SuggestedAction": action
    })

header = ["Timestamp", "Coin", "Sentiment", "PriceUSD", "SuggestedAction"]
exists = os.path.exists(history_file)

with open(history_file, "a", newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=header)
    if not exists:
        writer.writeheader()
    writer.writerows(rows)

# Plot chart
df = pd.DataFrame(sentiment_data)
summary = df.groupby(["Coin", "Source"])["Sentiment"].mean().reset_index()
summary["SuggestedAction"] = summary["Sentiment"].apply(suggest_action)
sentiment_summary = summary

fig, ax = plt.subplots(figsize=(10, 6))
for source in summary["Source"].unique():
    subset = summary[summary["Source"] == source]
    ax.bar(subset["Coin"] + " (" + source + ")", subset["Sentiment"], label=source)
ax.set_ylabel("Avg Sentiment")
ax.set_title("Crypto Sentiment Summary")
ax.axhline(0, color='gray', linestyle='--')
ax.legend()
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig(chart_file)
plt.show()

print(f"📈 Chart saved to {chart_file}")

# Telegram alerts
for coin in coins:
    avg_sent = df[df["Coin"] == coin]["Sentiment"].mean()
    action = suggest_action(avg_sent)
    message = f"\n🚨 Sentiment Alert for {coin}\nAvg Sentiment: {avg_sent:.2f}\nAction: {action}"
    send_telegram_message(message)
