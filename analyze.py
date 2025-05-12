# analyze.py
import os
import csv
import json
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

from analyze_sentiment import analyze_sentiment
from reddit_fetch    import fetch_reddit_posts
from rss_fetch       import fetch_rss_articles
from fetch_prices    import fetch_prices
from send_telegram   import send_telegram_message

# --- Configuration ---
coins         = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
output_file   = "sentiment_output.csv"
chart_file    = "sentiment_chart.png"
history_file  = "sentiment_history.csv"
telegram_chat = os.getenv("TELEGRAM_CHAT_ID")

def suggest_action(score):
    if score > 0.2:   return "📈 Consider Buying"
    if score < -0.2:  return "📉 Consider Selling"
    return "🤝 Hold / Watch"

sentiment_rows = []

print("🧠 Fetching Reddit sentiment...\n")
for coin in coins:
    for post in fetch_reddit_posts("CryptoCurrency", coin, 5):
        score  = analyze_sentiment(post["text"])
        action = suggest_action(score)
        sentiment_rows.append({
            "Source":    "Reddit",
            "Coin":       coin,
            "Text":       post["text"],
            "Sentiment":  score,
            "Action":     action,
            "Timestamp":  datetime.utcnow().isoformat(),
            "Link":       post["url"]
        })

print("\n📰 Fetching Crypto News sentiment...\n")
for coin in coins:
    for post in fetch_rss_articles(coin, 5):
        score  = analyze_sentiment(post["text"])
        action = suggest_action(score)
        sentiment_rows.append({
            "Source":    "News",
            "Coin":       coin,
            "Text":       post["text"],
            "Sentiment":  score,
            "Action":     action,
            "Timestamp":  datetime.utcnow().isoformat(),
            "Link":       post.get("link", "")
        })

# --- Save full dump ---
df = pd.DataFrame(sentiment_rows)
df.to_csv(output_file, index=False, encoding="utf-8")
print(f"✅ Sentiment results saved to {output_file}")

# --- Bar chart by coin & source ---
summary = df.groupby(["Coin", "Source"])["Sentiment"].mean().reset_index()
fig, ax = plt.subplots(figsize=(10,6))
for src in summary["Source"].unique():
    sub = summary[summary["Source"]==src]
    ax.bar(sub["Coin"]+" ("+src+")", sub["Sentiment"], label=src)
ax.axhline(0, color="gray", linestyle="--")
ax.set_ylabel("Avg Sentiment")
ax.set_title("Crypto Sentiment by Source")
ax.legend()
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(chart_file)
plt.show()
print(f"📈 Chart saved to {chart_file}")

# --- Telegram Alerts (per‐coin average across sources) ---
prices = fetch_prices()  # dict e.g. {"Bitcoin":56000,...}
coin_summary = (
    df.groupby("Coin")["Sentiment"]
      .mean()
      .reset_index()
      .assign(Action=lambda d: d["Sentiment"].apply(suggest_action))
)

for _, row in coin_summary.iterrows():
    msg = (
        f"🚨 Sentiment Alert for {row.Coin}\n"
        f"Avg Sentiment: {row.Sentiment:.2f}\n"
        f"Action: {row.Action}"
    )
    send_telegram_message(msg)

# --- Append to history CSV ---
hist_fields = ["Timestamp","Coin","Sentiment","PriceUSD","Action"]
new_rows = []
for _, row in coin_summary.iterrows():
    new_rows.append({
        "Timestamp":  datetime.utcnow().isoformat(),
        "Coin":       row.Coin,
        "Sentiment":  row.Sentiment,
        "PriceUSD":   prices.get(row.Coin, ""),
        "Action":     row.Action
    })

# ensure history file exists and has header
write_header = not os.path.exists(history_file)
with open(history_file, "a", newline="", encoding="utf-8") as hf:
    writer = csv.DictWriter(hf, fieldnames=hist_fields)
    if write_header:
        writer.writeheader()
    writer.writerows(new_rows)

print(f"✅ Appended {len(new_rows)} rows into {history_file}")
