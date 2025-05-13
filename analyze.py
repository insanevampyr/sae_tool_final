# analyze.py

import os
import csv
from datetime import datetime, timezone
from analyze_sentiment import analyze_sentiment
from reddit_fetch import fetch_reddit_posts
from rss_fetch import fetch_rss_articles
from fetch_prices import fetch_prices
from send_telegram import send_telegram_message
import pandas as pd

# --- CONFIG ---
coins = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
output_file  = "sentiment_output.csv"
history_file = "sentiment_history.csv"

def suggest_action(score):
    if score > 0.2:
        return "📈 Consider Buying"
    if score < -0.2:
        return "📉 Consider Selling"
    return "🤝 Hold / Watch"


# 1) Fetch raw posts
sentiment_rows = []
print("🧠 Fetching Reddit sentiment...\n")
for coin in coins:
    for post in fetch_reddit_posts("CryptoCurrency", coin, 5):
        score  = analyze_sentiment(post["text"])
        sentiment_rows.append({
            "Source":    "Reddit",
            "Coin":       coin,
            "Text":       post["text"],
            "Sentiment":  score,
            "Action":     suggest_action(score),
            "Timestamp":  datetime.now(timezone.utc).isoformat(),
            "Link":       post["url"],
        })

print("\n📰 Fetching Crypto News sentiment...\n")
for coin in coins:
    for post in fetch_rss_articles(coin, 5):
        score  = analyze_sentiment(post["text"])
        sentiment_rows.append({
            "Source":    "News",
            "Coin":       coin,
            "Text":       post["text"],
            "Sentiment":  score,
            "Action":     suggest_action(score),
            "Timestamp":  datetime.now(timezone.utc).isoformat(),
            "Link":       post.get("link", ""),
        })

# 2) Write or append raw output CSV
write_header = not os.path.exists(output_file)
with open(output_file, "a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=sentiment_rows[0].keys())
    if write_header:
        writer.writeheader()
    writer.writerows(sentiment_rows)
print(f"✅ Sentiment results {'created' if write_header else 'appended to'} {output_file}")

# 3) Build summary rows for history
prices = fetch_prices()  # returns e.g. {"Bitcoin": 12345.67, ...}

summary_rows = []
now = datetime.now(timezone.utc).isoformat()
for source in ("Reddit", "News"):
    df = pd.DataFrame([r for r in sentiment_rows if r["Source"] == source])
    if df.empty:
        continue
    grouped = df.groupby("Coin")["Sentiment"].mean().round(4)
    for coin, avg in grouped.items():
        summary_rows.append({
            "Timestamp":       now,
            "Coin":            coin,
            "Source":          source,
            "Sentiment":       avg,
            "PriceUSD":        prices.get(coin, ""),
            "SuggestedAction": suggest_action(avg),
        })

# 4) Write or append history CSV
history_header = ["Timestamp","Coin","Source","Sentiment","PriceUSD","SuggestedAction"]
write_hist_header = not os.path.exists(history_file)
with open(history_file, "a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=history_header)
    if write_hist_header:
        writer.writeheader()
    writer.writerows(summary_rows)
print(f"✅ History {'created' if write_hist_header else 'appended to'} {history_file}")

# 5) Telegram alerts for overall avg per coin (across both sources)
for coin in coins:
    all_avg = pd.DataFrame(summary_rows).query("Coin==@coin")["Sentiment"].mean()
    action = suggest_action(all_avg)
    msg = f"🚨 {coin} overall avg sentiment: {all_avg:.2f}\nSuggested: {action}"
    send_telegram_message(msg)

# analyze.py (at the very bottom)
import auto_push

if __name__ == "__main__":
    # ... all your existing analysis logic ...
    auto_push.auto_push()
