#!/usr/bin/env python3
import os
import json
import subprocess
from datetime import datetime, timezone, timedelta

import pandas as pd
from dotenv import load_dotenv
from telegram import Bot

from fetch_prices          import fetch_prices
from train_price_predictor import predict_prices   # now expects a DataFrame window
from analyze_sentiment     import get_latest_sentiment

# ─── CONFIG ────────────────────────────────────────────────────────────────
load_dotenv()
BOT        = Bot(token=os.getenv("TELEGRAM_TOKEN"))
CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID")
COINS      = ["Bitcoin","Ethereum","Solana","Dogecoin"]
HIST_CSV   = "sentiment_history.csv"
PRED_JSON  = "prediction_log.json"

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def ensure_pred_log():
    if not os.path.exists(PRED_JSON):
        save_json({c: [] for c in COINS}, PRED_JSON)

def send_hourly_alert():
    # 1) load & normalize history timestamps (mixed ISO8601)
    hist = pd.read_csv(HIST_CSV, parse_dates=["Timestamp"])
    hist["Timestamp"] = pd.to_datetime(
        hist["Timestamp"],
        utc=True,
        format="mixed",
        errors="coerce"
    )

    now     = datetime.now(timezone.utc)
    one_hr  = hist[hist["Timestamp"] >= now - timedelta(hours=1)]

    # 2) avg sentiment per coin
    avg_sent = one_hr.groupby("Coin").Sentiment.mean().round(3).to_dict()

    # 3) fetch current prices
    prices_now = fetch_prices(COINS)

    # 4) predict next‐hour prices, passing the sentiment window DataFrame
    preds = predict_prices(one_hr)

    # 5) compute 24 h accuracy
    log    = load_json(PRED_JSON)
    cutoff = now - timedelta(hours=24)
    acc    = {}
    for c, entries in log.items():
        recent  = [e for e in entries
                   if datetime.fromisoformat(e["timestamp"]) > cutoff]
        if recent:
            correct = sum(1 for e in recent if e.get("accurate"))
            acc[c]   = f"{round(correct / len(recent) * 100)}%"
        else:
            acc[c] = "–"

    # 6) build & send Telegram message
    parts = ["⏰ *Hourly Sentiment & Forecast*"]
    for c in COINS:
        s    = avg_sent.get(c, 0.0)
        pred = preds[c]["predicted"]
        by   = preds[c]["timestamp"][-5:]  # "HH:MM"
        a24  = acc[c]
        parts.append(
            f"*{c}*: avg sent {s:+.3f}\n"
            f"Now: ${prices_now[c]:.2f} → ${pred:.2f} by {by} UTC\n"
            f"24 h acc: {a24}"
        )

    BOT.send_message(
        chat_id=CHAT_ID,
        text="\n\n".join(parts),
        parse_mode="Markdown"
    )

def main():
    now_iso = datetime.now(timezone.utc).isoformat()

    # ─── A) append latest sentiment ──────────────────────────────────────────
    sent = get_latest_sentiment()  # { Timestamp,Coin,Source,Sentiment,PriceUSD,SuggestedAction }
    row  = ",".join(str(sent[k]) for k in ("Timestamp","Coin","Source","Sentiment","PriceUSD","SuggestedAction"))
    with open(HIST_CSV, "a", encoding="utf-8") as f:
        f.write(row + "\n")

    # ─── B) ensure & update preds ───────────────────────────────────────────
    ensure_pred_log()
    new_entry = {"timestamp": now_iso}
    prices    = fetch_prices(COINS)
    window    = pd.read_csv(HIST_CSV, parse_dates=["Timestamp"])
    for coin, info in predict_prices(window).items():
        curr   = prices[coin]
        pred   = info["predicted"]
        pct    = (pred - curr) / curr * 100 if curr else None
        new_entry[coin] = {
            "current":     curr,
            "predicted":   pred,
            "diff_pct":    round(pct, 2) if pct is not None else None,
            "timestamp":   now_iso,
            "accurate":    None
        }

    all_log = load_json(PRED_JSON)
    all_log.setdefault(coin, []).insert(0, new_entry)
    save_json(all_log, PRED_JSON)

    # ─── C) git add/commit/push & print updated files ───────────────────────
    subprocess.check_call(["git", "add", HIST_CSV, PRED_JSON])
    subprocess.check_call([
        "git", "commit", "-m",
        f"chore: auto-update @ {datetime.utcnow().isoformat()}Z"
    ], text=True)
    subprocess.check_call(["git", "push"], text=True)

    print("✅ Files updated/pushed:")
    print(f"  - {HIST_CSV}")
    print(f"  - {PRED_JSON}")

    # ─── D) send the Telegram alert ────────────────────────────────────────
    send_hourly_alert()

if __name__ == "__main__":
    main()
