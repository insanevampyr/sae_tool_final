import os
import sys
import json
import csv
import subprocess
from datetime import datetime, timezone, timedelta
import pandas as pd

from fetch_prices import fetch_prices
from analyze_sentiment import get_latest_sentiment
from train_price_predictor import predict_prices

# File paths
HIST_SENT_CSV = "sentiment_history.csv"
HIST_PRED_JSON = "prediction_log.json"

# Telegram setup (optional)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
try:
    from telegram import Bot
    bot = Bot(TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
except ImportError:
    bot = None


def append_sentiment():
    records = get_latest_sentiment()  # list of dicts
    # append CSV rows
    df = pd.read_csv(HIST_SENT_CSV) if os.path.exists(HIST_SENT_CSV) else pd.DataFrame()
    pd.concat([df, pd.DataFrame(records)], ignore_index=True).to_csv(HIST_SENT_CSV, index=False)
    print(f"✅ Appended {len(records)} sentiment rows")


def log_predictions():
    # auto-push via git
    try:
        subprocess.check_call(["git", "add", HIST_PRED_JSON])
        subprocess.check_call(["git", "commit", "-m", f"auto-update @ {now_iso}"])
        subprocess.check_call(["git", "push"])

        # **RESTORED PRINT OF UPDATED FILES**
        files = subprocess.check_output(
            ["git","diff-tree","--no-commit-id","--name-only","-r","HEAD"],
            text=True
        ).splitlines()
        print("✅ Files updated/pushed:")
        for f in files:
            print("  -", f)

    except subprocess.CalledProcessError as e:
        print("⚠️ Git push failed:", e)

    # write back
    with open(HIST_PRED_JSON, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)
    print("✅ Logged predictions to", HIST_PRED_JSON)

    # auto-push via git
    try:
        subprocess.check_call(["git", "add", HIST_PRED_JSON])
        subprocess.check_call(["git", "commit", "-m", f"auto-update @ {now_iso}"])
        subprocess.check_call(["git", "push"]);
        # list files
        files = subprocess.check_output([
            "git","diff-tree","--no-commit-id","--name-only","-r","HEAD"
        ], text=True).splitlines()
        print("✅ Files updated/pushed:")
        for f in files:
            print("  -", f)
    except subprocess.CalledProcessError as e:
        print("⚠️ Git push failed:", e)


def send_hourly_alert():
    # prepare hourly summary
    df = pd.read_csv(HIST_SENT_CSV, parse_dates=["Timestamp"] )
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = df[df.Timestamp >= cutoff]
    if recent.empty:
        return

    msg = [f"📈 Sentiment Summary (last hour):"]
    for coin, grp in recent.groupby("Coin"):
        avg_sent = grp.Sentiment.mean()
        msg.append(f"*{coin}*: avg {avg_sent:+.3f} ({len(grp)} posts)")

    alert = "\n".join(msg)
    print(alert)
    if bot and TELEGRAM_CHAT_ID:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=alert, parse_mode='Markdown')
        print("✅ Telegram alert sent.")


def main():
    append_sentiment()
    log_predictions()
    send_hourly_alert()


if __name__ == "__main__":
    main()
