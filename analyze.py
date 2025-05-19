#!/usr/bin/env python3
# analyze.py

import os
import json
import subprocess
from datetime import datetime, timezone, timedelta

import pandas as pd
from dateutil import parser
from dotenv import load_dotenv
from telegram import Bot

from fetch_prices import fetch_prices
from analyze_sentiment import get_latest_sentiment
from train_price_predictor import predict_prices

# ─── CONFIG ────────────────────────────────────────────────────────────────
load_dotenv()
HIST_SENT_CSV  = "sentiment_history.csv"
PRED_LOG_JSON  = "prediction_log.json"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT  = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
COINS = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]


def append_sentiment():
    """Fetch latest sentiment rows and append to CSV."""
    records = get_latest_sentiment()  # list of dicts
    df = pd.read_csv(HIST_SENT_CSV) if os.path.exists(HIST_SENT_CSV) else pd.DataFrame()
    pd.concat([df, pd.DataFrame(records)], ignore_index=True) \
      .to_csv(HIST_SENT_CSV, index=False)
    print(f"✅ Appended {len(records)} sentiment rows")


def log_predictions(window_hours: int = 3):
    """Generate next-hour forecasts for every coin, record to JSON, commit & push."""
    # load full history
    hist = pd.read_csv(HIST_SENT_CSV)
    # robust ISO-8601 parsing
    hist["Timestamp"] = hist["Timestamp"].apply(parser.isoparse)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)

    # load or init log
    if os.path.exists(PRED_LOG_JSON):
        log = json.load(open(PRED_LOG_JSON))
    else:
        log = {coin: [] for coin in COINS}

    # fetch live prices for all coins
    price_df = fetch_prices(COINS)
    curr_map = dict(zip(price_df.Coin, price_df.PriceUSD))

    for coin in COINS:
        curr = curr_map.get(coin)

        # average sentiment in window
        window = hist[(hist.Coin == coin) & (hist.Timestamp >= cutoff)]["Sentiment"]
        if not window.empty:
            avg_sent = window.mean()
        else:
            all_hist = hist[hist.Coin == coin]
            avg_sent = all_hist["Sentiment"].iloc[-1] if not all_hist.empty else None

        # predict up/down
        if curr is not None and avg_sent is not None:
            label = predict_prices(pd.DataFrame({"AvgSentiment": [avg_sent]}))[0]
            predicted = curr * (1.01 if label == 1 else 0.99)
            diff_pct = round((predicted - curr) / curr * 100, 2)
        else:
            predicted, diff_pct = None, None

        entry = {
            "timestamp": now.isoformat(),
            "current":   curr,
            "predicted": predicted,
            "diff_pct":  diff_pct,
            "accurate":  None
        }
        log.setdefault(coin, []).insert(0, entry)

    # write back
    with open(PRED_LOG_JSON, "w") as f:
        json.dump(log, f, indent=2)

    # commit & push
    try:
        subprocess.check_call(["git", "add", HIST_SENT_CSV, PRED_LOG_JSON])
        subprocess.check_call(["git", "commit", "-m", f"auto-update @ {now.isoformat()}"])
        subprocess.check_call(["git", "push"])
        print("✅ Logged predictions and pushed to git")
    except subprocess.CalledProcessError as e:
        print("❌ Git operation failed:", e)


def main():
    append_sentiment()
    log_predictions(window_hours=3)


if __name__ == "__main__":
    main()
