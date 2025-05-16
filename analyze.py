# analyze.py
import os, csv, json, subprocess
from datetime import datetime, timezone, timedelta
import pandas as pd

from analyze_sentiment import analyze_sentiment
from reddit_fetch import fetch_reddit_posts
from rss_fetch import fetch_rss_articles
from fetch_prices import fetch_prices
from send_telegram import send_telegram_message
import auto_push

# --- CONFIG ---
coins = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
output_file = "sentiment_output.csv"
history_file = "sentiment_history.csv"
ml_log_path = "prediction_log.json"
tolerance_pct = 4  # accuracy threshold in percent

# --- Utility functions ---
def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def remove_duplicates(path, subset):
    df = pd.read_csv(path)
    df.drop_duplicates(subset=subset, keep="last", inplace=True)
    df.to_csv(path, index=False)

# --- Prediction log initializer & updater ---
def update_predictions():
    # If log file missing or corrupted, initialize with empty lists
    if not os.path.exists(ml_log_path):
        default_log = {coin: [] for coin in coins}
        save_json(default_log, ml_log_path)
        print(f"✅ Initialized new {ml_log_path}")
        return

    log = load_json(ml_log_path)
    if not log:
        # handle empty or invalid JSON by reinitializing
        default_log = {coin: [] for coin in coins}
        save_json(default_log, ml_log_path)
        print(f"✅ Reinitialized corrupted {ml_log_path}")
        return

    hist_df = pd.read_csv(history_file)
    hist_df["Timestamp"] = pd.to_datetime(hist_df["Timestamp"], utc=True, errors="coerce")
    changed = False
    now = datetime.now(timezone.utc)

    for coin, entries in log.items():
        for entry in entries:
            if entry.get("actual") is not None:
                continue
            ts_str = entry.get("timestamp", "").replace('+00:00','')
            try:
                t0 = datetime.fromisoformat(ts_str)
            except ValueError:
                continue
            if now - t0 < timedelta(hours=1):
                continue
            match = hist_df[
                (hist_df["Coin"] == coin) &
                (hist_df["Timestamp"] > t0)
            ].sort_values("Timestamp")
            if not match.empty:
                actual_price = float(match.iloc[0].get("PriceUSD", 0))
                err_pct = abs((entry.get("predicted",0) - actual_price) / actual_price) * 100
                entry["actual"] = round(actual_price, 2)
                entry["diff_pct"] = round(err_pct, 2)
                entry["accurate"] = err_pct <= tolerance_pct
                changed = True

    if changed:
        save_json(log, ml_log_path)
        print(f"✅ Updated {ml_log_path} with actual prices")

# --- Main script ---
def main():
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    sentiment_rows = []

    # Fetch Reddit sentiment
    for coin in coins:
        for post in fetch_reddit_posts("CryptoCurrency", coin, 5):
            score = analyze_sentiment(post.get("text", ""))
            sentiment_rows.append({
                "Source": "Reddit",
                "Coin": coin,
                "Text": post.get("text", ""),
                "Sentiment": score,
                "Action": ("📈 Consider Buying" if score > 0.2 else "📉 Consider Selling" if score < -0.2 else "🤝 Hold / Watch"),
                "Timestamp": now_iso,
                "Link": post.get("url", ""),
            })

    # Fetch News sentiment
    for coin in coins:
        for post in fetch_rss_articles(coin, 5):
            score = analyze_sentiment(post.get("text", ""))
            sentiment_rows.append({
                "Source": "News",
                "Coin": coin,
                "Text": post.get("text", ""),
                "Sentiment": score,
                "Action": ("📈 Consider Buying" if score > 0.2 else "📉 Consider Selling" if score < -0.2 else "🤝 Hold / Watch"),
                "Timestamp": now_iso,
                "Link": post.get("link", ""),
            })

    # Write/append sentiment_output.csv and dedupe
    write_header = not os.path.exists(output_file)
    with open(output_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sentiment_rows[0].keys())
        if write_header:
            writer.writeheader()
        writer.writerows(sentiment_rows)
    remove_duplicates(output_file, ["Timestamp", "Coin", "Source", "Text"])

    # Build and append history rows
    prices = fetch_prices()
    summary_rows = []
    df_all = pd.DataFrame(sentiment_rows)
    for source in ("Reddit", "News"):
        df = df_all[df_all["Source"] == source]
        if df.empty:
            continue
        grouped = df.groupby("Coin")["Sentiment"].mean().round(4)
        for coin, avg in grouped.items():
            summary_rows.append({
                "Timestamp": now_iso,
                "Coin": coin,
                "Source": source,
                "Sentiment": avg,
                "PriceUSD": prices.get(coin, ""),
                "SuggestedAction": ("📈 Consider Buying" if avg > 0.2 else "📉 Consider Selling" if avg < -0.2 else "🤝 Hold / Watch"),
            })
    write_hist_header = not os.path.exists(history_file)
    with open(history_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_rows[0].keys())
        if write_hist_header:
            writer.writeheader()
        writer.writerows(summary_rows)
    remove_duplicates(history_file, ["Timestamp", "Coin", "Source"])

    # Telegram alerts
    for coin in coins:
        avg = pd.DataFrame(summary_rows).query("Coin==@coin")["Sentiment"].mean()
        send_telegram_message(f"🚨 {coin} avg sentiment: {avg:.2f}\nSuggested: {('📈 Consider Buying' if avg>0.2 else '📉 Consider Selling' if avg< -0.2 else '🤝 Hold / Watch')}")

    # Update prediction log and auto-push
    update_predictions()
    auto_push.auto_push()

    # Print files committed in last push
    try:
        last_files = subprocess.check_output(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
            text=True
        ).splitlines()
        print("✅ Files updated/pushed in last commit:")
        for f in last_files:
            print(f" - {f}")
    except Exception as e:
        print(f"⚠️ Could not list committed files: {e}")

if __name__ == "__main__":
    main()
