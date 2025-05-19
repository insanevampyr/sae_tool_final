#!/usr/bin/env python3
# analyze.py

import os
import csv
import json
import subprocess
from datetime import datetime, timezone, timedelta

import pandas as pd
from dateutil import parser
from dotenv import load_dotenv

from reddit_fetch          import fetch_reddit_posts
from rss_fetch             import fetch_rss_articles
from analyze_sentiment     import analyze_sentiment
from fetch_prices          import fetch_prices
from train_price_predictor import predict_prices
from send_telegram         import send_telegram_message
import auto_push

# ─── CONFIG ────────────────────────────────────────────────────────────────
load_dotenv()
COINS          = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
OUT_CSV        = "sentiment_output.csv"
HIST_CSV       = "sentiment_history.csv"
PRED_LOG_JSON  = "prediction_log.json"
ALERT_LOG_JSON = "alert_log.json"
TOL_PCT        = 4  # ML accuracy threshold (%)

# ─── HELPERS ────────────────────────────────────────────────────────────────
def load_json(path):
    if os.path.exists(path):
        try:
            return json.load(open(path, "r", encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}

def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def dedupe_csv(path, subset):
    if not os.path.exists(path):
        return
    df    = pd.read_csv(path)
    valid = [c for c in subset if c in df.columns]
    if valid:
        df.drop_duplicates(subset=valid, keep="last", inplace=True)
        df.to_csv(path, index=False)

def ensure_pred_log():
    if not os.path.exists(PRED_LOG_JSON):
        save_json({c: [] for c in COINS}, PRED_LOG_JSON)

def update_predictions_with_actuals():
    log  = load_json(PRED_LOG_JSON)
    hist = pd.read_csv(HIST_CSV)
    hist["Timestamp"] = hist["Timestamp"].apply(parser.isoparse).apply(lambda dt: dt.replace(tzinfo=None))
    now     = datetime.utcnow()
    changed = False

    for coin, entries in log.items():
        for e in entries:
            # skip if no predicted, or already filled
            if "actual" in e or "predicted" not in e:
                continue
            t0 = parser.isoparse(e["timestamp"]).replace(tzinfo=None)
            if now - t0 < timedelta(hours=1):
                continue
            sub = hist[(hist.Coin == coin) & (hist.Timestamp > t0)]
            if not sub.empty:
                actual      = float(sub.iloc[0].PriceUSD)
                pct         = abs(e["predicted"] - actual) / actual * 100 if actual else None
                e["actual"]   = round(actual, 2)
                e["diff_pct"] = round(pct, 2) if pct is not None else None
                e["accurate"] = (pct is not None and pct <= TOL_PCT)
                changed = True

    if changed:
        save_json(log, PRED_LOG_JSON)

# ─── MAIN ───────────────────────────────────────────────────────────────────
def main():
    now    = datetime.utcnow().replace(tzinfo=timezone.utc)
    ts_iso = now.isoformat()

    # 1) Scrape & analyze
    rows = []
    for coin in COINS:
        # reddit
        for post in fetch_reddit_posts([coin])[:5]:
            text = post.get("Text", "")
            s    = analyze_sentiment(text)
            rows.append({
                "Timestamp": ts_iso, "Coin": coin,
                "Source":    "Reddit", "Text": text,
                "Sentiment": s
            })
        # news
        for art in fetch_rss_articles(coin)[:5]:
            text = art.get("text", "")
            s    = analyze_sentiment(text)
            rows.append({
                "Timestamp": ts_iso, "Coin": coin,
                "Source":    "News",   "Text": text,
                "Sentiment": s
            })

    header1 = not os.path.exists(OUT_CSV)
    with open(OUT_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        if header1: w.writeheader()
        w.writerows(rows)
    dedupe_csv(OUT_CSV, ["Timestamp", "Coin", "Source", "Text"])

    # 2) Append to history
    prices    = fetch_prices(COINS).set_index("Coin")["PriceUSD"].to_dict()
    hist_rows = []
    df        = pd.DataFrame(rows)
    for src in ("Reddit", "News"):
        sub = df[df.Source == src]
        for coin, avg in sub.groupby("Coin")["Sentiment"].mean().items():
            price  = prices.get(coin, 0.0)
            action = (
                "📈 Buy"  if avg > 0.2 else
                "📉 Sell" if avg < -0.2 else
                "🤝 Hold"
            )
            hist_rows.append({
                "Timestamp":       ts_iso,
                "Coin":            coin,
                "Source":          src,
                "Sentiment":       round(avg, 4),
                "PriceUSD":        round(price, 2),
                "SuggestedAction": action
            })

    header2 = not os.path.exists(HIST_CSV)
    with open(HIST_CSV, "a", newline="", encoding="utf-8") as f:
        w2 = csv.DictWriter(f, fieldnames=hist_rows[0].keys())
        if header2: w2.writeheader()
        w2.writerows(hist_rows)
    dedupe_csv(HIST_CSV, ["Timestamp", "Coin", "Source"])

    # 3) Always log next-hour predictions
    ensure_pred_log()
    full = pd.read_csv(HIST_CSV)
    full["Timestamp"] = full["Timestamp"].apply(parser.isoparse)
    cutoff   = now - timedelta(hours=1)
    avg_sents = [
        full[(full.Coin==coin)&(full.Timestamp>cutoff)]["Sentiment"].mean() or 0.0
        for coin in COINS
    ]

    preds = predict_prices(pd.DataFrame({"AvgSentiment": avg_sents}))
    log   = load_json(PRED_LOG_JSON)
    for coin, p in zip(COINS, preds):
        entry = {"timestamp": ts_iso, "predicted": round(float(p), 2)}
        log[coin].insert(0, entry)
    save_json(log, PRED_LOG_JSON)
    print(f"📝 prediction_log.json updated with: {dict(zip(COINS, preds))}")

    # 4) Hourly Telegram Alert
    alert = load_json(ALERT_LOG_JSON)
    last  = parser.isoparse(alert["last_alert"]) if alert.get("last_alert") else None
    send  = (last is None or (now - last >= timedelta(hours=1)))

    if send:
        # 4a) Sentiment (last hr)
        sent_lines = ["Sentiment (last hr)"]
        for coin, avg in zip(COINS, avg_sents):
            sent_lines.append(f"{coin}: {avg:+.2f}")

        # 4b) 24h Prediction Accuracy
        acc_lines = ["24h Prediction Acc"]
        for coin in COINS:
            entries = log.get(coin, [])
            acc = next((e.get("accurate", True) for e in entries if "accurate" in e), True)
            acc_lines.append(f"{coin}: {int(acc)*100}%")

        # 4c) Next Hour Forecast
        next_lines = ["Next Hour Forecast"]
        for coin, p in zip(COINS, preds):
            t1     = (now + timedelta(hours=1)).strftime("%H:%M UTC")
            curr   = prices.get(coin, 0.0)
            change = (p - curr) / curr * 100 if curr else 0.0
            arrow  = "↑" if change >= 0 else "↓"
            next_lines.append(f"{coin} by {t1}: ${p:,.2f} ({arrow}{abs(change):.1f}%)")

        body = "\n\n".join([
            "⏰ Hourly Sentiment & Forecast",
            "\n".join(sent_lines),
            "\n".join(acc_lines),
            "\n".join(next_lines),
        ])
        send_telegram_message(body)
        alert["last_alert"] = ts_iso
        save_json(alert, ALERT_LOG_JSON)

    # 5) Update actuals & auto-push
    update_predictions_with_actuals()
    auto_push.auto_push()

    # 6) Commit-diff helper
    try:
        files = subprocess.check_output(
            ["git","diff-tree","--no-commit-id","--name-only","-r","HEAD"],
            text=True
        ).splitlines()
        print("✅ Files updated in last commit:")
        for f in files:
            print(" -", f)
    except Exception as e:
        print("⚠️ Diff helper error:", e)

if __name__ == "__main__":
    main()
