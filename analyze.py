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

coins = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
output_file = "sentiment_output.csv"
chart_file = "sentiment_chart.png"
history_file = "sentiment_history.csv"

def suggest_action(score):
    if score > 0.2:
        return "📈 Consider Buying"
    elif score < -0.2:
        return "📉 Consider Selling"
    else:
        return "🤝 Hold / Watch"

sentiment_data = []

print("\U0001F9E0 Fetching Reddit sentiment...\n")
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
            "Link": post["url"]
        })

print("\n\U0001F4F0 Fetching Crypto News sentiment...\n")
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
            "Link": post["url"]
        })

# Save to output CSV
with open(output_file, "w", newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=sentiment_data[0].keys())
    writer.writeheader()
    writer.writerows(sentiment_data)

print(f"\n✅ Sentiment results saved to {output_file}")

# Append to sentiment history
history_exists = os.path.exists(history_file)
with open(history_file, "a", newline='', encoding='utf-8') as hf:
    writer = csv.DictWriter(hf, fieldnames=sentiment_data[0].keys())
    if not history_exists:
        writer.writeheader()
    writer.writerows(sentiment_data)

# Aggregate & visualize
df = pd.DataFrame(sentiment_data)
summary = df.groupby(["Coin", "Source"])["Sentiment"].mean().reset_index()
summary["SuggestedAction"] = summary["Sentiment"].apply(suggest_action)

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
