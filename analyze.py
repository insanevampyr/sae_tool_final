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
    # 1) Fetch sentiment data
    sentiment_rows = []
    now_ts = datetime.now(timezone.utc).isoformat()

    for coin in coins:
        for post in fetch_reddit_posts("CryptoCurrency", coin, 5):
            sentiment_rows.append({
                "Source":    "Reddit",
                "Coin":       coin,
                "Text":       post["text"],
                "Sentiment":  analyze_sentiment(post["text"]),
                "Action":     suggest_action(analyze_sentiment(post["text"])),
                "Timestamp":  now_ts,
                "Link":       post["url"],
            })

        for post in fetch_rss_articles(coin, 5):
            sentiment_rows.append({
                "Source":    "News",
                "Coin":       coin,
                "Text":       post["text"],
                "Sentiment":  analyze_sentiment(post["text"]),
                "Action":     suggest_action(analyze_sentiment(post["text"])),
                "Timestamp":  now_ts,
                "Link":       post.get("link", ""),
            })

    # 2) Remove duplicates vs existing output
    if os.path.exists(output_file):
        old_df = pd.read_csv(output_file)
        combined_df = pd.concat([old_df, pd.DataFrame(sentiment_rows)], ignore_index=True)
        combined_df.drop_duplicates(subset=["Coin", "Source", "Text"], inplace=True)
    else:
        combined_df = pd.DataFrame(sentiment_rows)

    combined_df.to_csv(output_file, index=False)
    print(f"✅ Written: {len(sentiment_rows)} entries to {output_file}")

    # 3) Append historical data
    prices = fetch_prices()
    summary_rows = []
    for source in ("Reddit", "News"):
        df = combined_df[combined_df["Source"] == source]
        grouped = df.groupby("Coin")["Sentiment"].mean().round(4)
        for coin, avg in grouped.items():
            summary_rows.append({
                "Timestamp":       now_ts,
                "Coin":            coin,
                "Source":          source,
                "Sentiment":       avg,
                "PriceUSD":        prices.get(coin, ""),
                "SuggestedAction": suggest_action(avg),
            })

    hist_df = pd.DataFrame(summary_rows)
    if os.path.exists(history_file):
        hist_old = pd.read_csv(history_file)
        hist_df = pd.concat([hist_old, hist_df], ignore_index=True)
        hist_df.drop_duplicates(subset=["Timestamp", "Coin", "Source"], inplace=True)

    hist_df.to_csv(history_file, index=False)
    print(f"✅ Updated: {history_file}")

    # 4) Telegram alerts
    for coin in coins:
        avg = hist_df.query("Coin == @coin")["Sentiment"].mean()
        msg = f"🚨 {coin} overall avg sentiment: {avg:.2f}\nSuggested: {suggest_action(avg)}"
        send_telegram_message(msg)

if __name__ == "__main__":
    main()
    auto_push.auto_push()
