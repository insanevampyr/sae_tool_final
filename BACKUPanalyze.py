# analyze.py

import os
import csv
from datetime import datetime, timezone
import pandas as pd

from analyze_sentiment import analyze_sentiment
from reddit_fetch import fetch_reddit_posts
from rss_fetch import fetch_rss_articles
from fetch_prices import fetch_prices
from send_telegram import send_telegram_message

# auto_push.py must live alongside this file
import auto_push

# --- CONFIG ---
coins = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
output_file  = "sentiment_output.csv"
history_file = "sentiment_history.csv"

def suggest_action(score: float) -> str:
    if score > 0.2:
        return "📈 Consider Buying"
    if score < -0.2:
        return "📉 Consider Selling"
    return "🤝 Hold / Watch"

def main():
    # 1) Fetch raw posts
    sentiment_rows = []
    print("🧠 Fetching Reddit sentiment…")
    for coin in coins:
        for post in fetch_reddit_posts("CryptoCurrency", coin, 5):
            score = analyze_sentiment(post["text"])
            sentiment_rows.append({
                "Source":    "Reddit",
                "Coin":       coin,
                "Text":       post["text"],
                "Sentiment":  score,
                "Action":     suggest_action(score),
                "Timestamp":  datetime.now(timezone.utc).isoformat(),
                "Link":       post["url"],
            })

    print("📰 Fetching Crypto News sentiment…")
    for coin in coins:
        for post in fetch_rss_articles(coin, 5):
            score = analyze_sentiment(post["text"])
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
    prices = fetch_prices()
    summary_rows = []
    now_iso = datetime.now(timezone.utc).isoformat()

    df_all = pd.DataFrame(sentiment_rows)
    for source in ("Reddit", "News"):
        df = df_all[df_all["Source"] == source]
        if df.empty:
            continue
        grouped = df.groupby("Coin")["Sentiment"].mean().round(4)
        for coin, avg in grouped.items():
            summary_rows.append({
                "Timestamp":       now_iso,
                "Coin":            coin,
                "Source":          source,
                "Sentiment":       avg,
                "PriceUSD":        prices.get(coin, ""),
                "SuggestedAction": suggest_action(avg),
            })

    # 4) Write or append history CSV
    history_fields = ["Timestamp","Coin","Source","Sentiment","PriceUSD","SuggestedAction"]
    write_hist_header = not os.path.exists(history_file)
    with open(history_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=history_fields)
        if write_hist_header:
            writer.writeheader()
        writer.writerows(summary_rows)
    print(f"✅ History {'created' if write_hist_header else 'appended to'} {history_file}")

    # 5) Telegram alerts for overall avg per coin (across both sources)
    for coin in coins:
        overall_avg = (
            pd.DataFrame(summary_rows)
              .query("Coin == @coin")["Sentiment"]
              .mean()
        )
        action = suggest_action(overall_avg)
        msg = f"🚨 {coin} overall avg sentiment: {overall_avg:.2f}\nSuggested: {action}"
        send_telegram_message(msg)

if __name__ == "__main__":
    main()
    auto_push.auto_push()
