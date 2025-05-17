#!/usr/bin/env python3
import os, json, csv, subprocess
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from telegram import Bot
import pandas as pd

from analyze_sentiment import get_latest_sentiment
from fetch_prices import fetch_prices
from train_price_predictor import predict_prices

# ─── CONFIG ────────────────────────────────────────────────────────────────
load_dotenv()
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HIST_CSV    = "sentiment_history.csv"
PRED_LOG    = "prediction_log.json"

bot = Bot(TELEGRAM_TOKEN)

# ─── HELPERS ───────────────────────────────────────────────────────────────
def compute_24h_accuracy(coin):
    now = datetime.now(timezone.utc)
    with open(PRED_LOG, "r", encoding="utf-8") as f:
        log = json.load(f)
    cutoff = now - timedelta(hours=24)
    entries = [e for e in log.get(coin, [])
               if datetime.fromisoformat(e["timestamp"]) > cutoff and e.get("accurate") is not None]
    total = len(entries)
    correct = sum(1 for e in entries if e.get("accurate"))
    return f"{correct}/{total} ({correct/total*100:.0f}% )" if total else "–"

# ─── ALERT ─────────────────────────────────────────────────────────────────
def send_hourly_alert():
    # load historical sentiment
    hist = pd.read_csv(HIST_CSV, parse_dates=["Timestamp"] )
    hist["Timestamp"] = pd.to_datetime(hist["Timestamp"], utc=True)
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    last_hour = hist[hist.Timestamp >= one_hour_ago]

    # average sentiment last hour
    avg = last_hour.groupby("Coin").Sentiment.mean().round(3).to_dict()

    # fetch prices and ML predictions
    prices = fetch_prices()
    preds  = predict_prices(last_hour, prices)

    # build message
    lines = ["*Hourly Sentiment & Next-Hour ML Forecast*",
             f"_{now.strftime('%Y-%m-%d %H:%M UTC')}_", ""]
    for coin in prices:
        pct24 = compute_24h_accuracy(coin)
        lines.append(
            f"*{coin}* | Sent {avg.get(coin,'–'):+.3f} | Now ${prices[coin]:.2f} | -> ${preds[coin]:.2f} by {(now+timedelta(hours=1)).strftime('%H:%M')} UTC | {pct24} acc"
        )
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="\n".join(lines), parse_mode="Markdown")

# ─── MAIN ──────────────────────────────────────────────────────────────────
def main():
    # 1) append latest sentiment
    sent = get_latest_sentiment()
    with open(HIST_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sent.keys())
        if f.tell() == 0:
            writer.writeheader()
        writer.writerow(sent)

    # 2) append ML prediction to log
    now = datetime.now(timezone.utc).isoformat()
    prices = fetch_prices()
    preds  = predict_prices(pd.DataFrame([sent]), prices)
    log = json.loads(open(PRED_LOG).read() or "{}")
    for c, pred in preds.items():
        entry = {"timestamp": now, "predicted": pred, "accurate": None}
        log.setdefault(c, []).append(entry)
    with open(PRED_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

    # 3) send telegram alert
    send_hourly_alert()

    # 4) git add, commit, push
    subprocess.check_call(["git", "add", HIST_CSV, PRED_LOG])
    subprocess.check_call(["git", "commit", "-m", f"auto-update @ {now}"])
    subprocess.check_call(["git", "push"] )

    # 5) print updated files
    try:
        files = subprocess.check_output(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], text=True
        ).splitlines()
        print("✅ Files updated/pushed:")
        for f in files:
            print(f"  - {f}")
    except Exception as e:
        print(f"⚠️ Could not list files: {e}")

if __name__ == "__main__":
    main()
