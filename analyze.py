# analyze.py
import os, csv, json
from datetime import datetime, timezone, timedelta
import pandas as pd

from analyze_sentiment import analyze_sentiment
from reddit_fetch      import fetch_reddit_posts
from rss_fetch         import fetch_rss_articles
from fetch_prices      import fetch_prices
from send_telegram     import send_telegram_message
import auto_push

# --- CONFIG ---
coins        = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
output_file  = "sentiment_output.csv"
history_file = "sentiment_history.csv"
ml_log_path  = "prediction_log.json"

def suggest_action(score: float) -> str:
    if score > 0.2:  return "📈 Consider Buying"
    if score < -0.2: return "📉 Consider Selling"
    return "🤝 Hold / Watch"

def load_json(path):
    return json.load(open(path)) if os.path.exists(path) else {}

def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def remove_duplicates(file_path, subset):
    df = pd.read_csv(file_path)
    df.drop_duplicates(subset=subset, keep="last", inplace=True)
    df.to_csv(file_path, index=False)

def update_predictions():
    """Fill in actual prices and accuracy for any predictions older than 1h."""
    tolerance = 4
    log = load_json(ml_log_path)
    if not os.path.exists(history_file):
        return
    hist_df = pd.read_csv(history_file)
    hist_df["Timestamp"] = pd.to_datetime(hist_df["Timestamp"], utc=True, errors="coerce")

    changed = False
    for coin, entries in log.items():
        for entry in entries:
            if entry.get("actual") is not None:
                continue
            t = pd.to_datetime(entry["timestamp"], utc=True)
            if datetime.now(timezone.utc) - t < timedelta(hours=1):
                continue

            match = hist_df[
                (hist_df["Coin"] == coin) &
                (hist_df["Timestamp"] > t)
            ].sort_values("Timestamp")

            if not match.empty:
                actual_price = match.iloc[0]["PriceUSD"]
                entry["actual"]   = round(actual_price, 2)
                err = abs((entry["predicted"] - actual_price) / actual_price) * 100
                entry["diff_pct"] = round(err, 2)
                entry["accurate"] = err <= tolerance
                changed = True

    if changed:
        save_json(log, ml_log_path)
        print("✅ prediction_log.json updated with actual prices")

def main():
    now = datetime.now(timezone.utc)
    sentiment_rows = []

    # 1) Fetch raw sentiment
    for coin in coins:
        for post in fetch_reddit_posts("CryptoCurrency", coin, 5):
            score = analyze_sentiment(post["text"])
            sentiment_rows.append({
                "Source":    "Reddit",
                "Coin":       coin,
                "Text":       post["text"],
                "Sentiment":  score,
                "Action":     suggest_action(score),
                "Timestamp":  now.isoformat(),
                "Link":       post["url"],
            })
        for post in fetch_rss_articles(coin, 5):
            score = analyze_sentiment(post["text"])
            sentiment_rows.append({
                "Source":    "News",
                "Coin":       coin,
                "Text":       post["text"],
                "Sentiment":  score,
                "Action":     suggest_action(score),
                "Timestamp":  now.isoformat(),
                "Link":       post.get("link", ""),
            })

    # 2) Write & dedupe output CSV
    write_header = not os.path.exists(output_file)
    with open(output_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sentiment_rows[0].keys())
        if write_header:
            writer.writeheader()
        writer.writerows(sentiment_rows)
    remove_duplicates(output_file, ["Timestamp", "Coin", "Source", "Text"])
    print(f"✅ Written: {len(sentiment_rows)} entries to {output_file}")

    # 3) Build & append history
    prices     = fetch_prices()
    summary_rows = []
    for source in ("Reddit", "News"):
        df = pd.DataFrame(sentiment_rows)
        df = df[df["Source"] == source]
        grouped = df.groupby("Coin")["Sentiment"].mean().round(4)
        for coin, avg in grouped.items():
            summary_rows.append({
                "Timestamp":       now.isoformat(),
                "Coin":            coin,
                "Source":          source,
                "Sentiment":       avg,
                "PriceUSD":        prices.get(coin, ""),
                "SuggestedAction": suggest_action(avg),
            })

    write_header = not os.path.exists(history_file)
    with open(history_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_rows[0].keys())
        if write_header:
            writer.writeheader()
        writer.writerows(summary_rows)
    remove_duplicates(history_file, ["Timestamp", "Coin", "Source"])
    print(f"✅ History updated at {history_file}")

    # 4) Alerts on Telegram
    for coin in coins:
        avg = pd.DataFrame(summary_rows).query("Coin == @coin")["Sentiment"].mean()
        send_telegram_message(f"🚨 {coin} avg sentiment: {avg:.2f}\nSuggested: {suggest_action(avg)}")

    # 5) Enrich prediction_log.json with actuals
    update_predictions()

    # 6) Auto-push
    auto_push.auto_push()

if __name__ == "__main__":
    main()
