#!/usr/bin/env python3
import os, csv, json, subprocess
from datetime import datetime, timezone, timedelta
import pandas as pd

from reddit_fetch        import fetch_reddit_posts
from rss_fetch           import fetch_rss_articles
from analyze_sentiment   import analyze_sentiment
from fetch_prices        import fetch_prices
from train_price_predictor import predict_prices, train_and_save
from send_telegram       import send_telegram_message
import auto_push

# ─── CONFIG ─────────────────────────────────────────────────────────────────
COINS         = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
HIST_CSV      = "sentiment_history.csv"
PRED_LOG_JSON = "prediction_log.json"
ALERT_LOG_JSON= "alert_log.json"
TOL_PCT       = 4  # accuracy threshold for “accurate” flag

def load_json(path):
    if os.path.exists(path):
        try:
            return json.load(open(path, 'r', encoding='utf-8'))
        except json.JSONDecodeError:
            return {}
    return {}

def save_json(obj, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2)

def ensure_pred_log():
    if not os.path.exists(PRED_LOG_JSON):
        init = {c: [] for c in COINS}
        save_json(init, PRED_LOG_JSON)

def update_predictions_with_actuals():
    log = load_json(PRED_LOG_JSON)
    hist = pd.read_csv(HIST_CSV)
    hist['Timestamp'] = pd.to_datetime(hist['Timestamp'], utc=True)
    now = datetime.now(timezone.utc)
    changed = False

    for coin, entries in log.items():
        for e in entries:
            if 'actual' in e:
                continue
            t0 = datetime.fromisoformat(e['timestamp'])
            if now - t0 < timedelta(hours=1):
                continue
            sub = hist[(hist.Coin == coin) & (hist.Timestamp > t0)]
            if not sub.empty:
                actual = float(sub.iloc[0].PriceUSD)
                e['actual'] = round(actual, 2)
                diff = abs(e['predicted'] - actual)
                pct  = diff / actual * 100 if actual else None
                e['diff_pct'] = round(pct, 2) if pct is not None else None
                e['accurate'] = (pct is not None and pct <= TOL_PCT)
                changed = True

    if changed:
        save_json(log, PRED_LOG_JSON)

def main():
    now    = datetime.now(timezone.utc)
    ts_iso = now.isoformat()

    # … your scraping & history‐append code stays the same until…
    # After you write sentiment_history.csv and commit it…

    # TRAIN/UPDATE the regression models
    train_price_predictor.train_and_save()

    # 4) Compute Next‐Hour Predictions
    # Load latest sentiment averages from history
    full = pd.read_csv(HIST_CSV)
    full['Timestamp'] = pd.to_datetime(full['Timestamp'], utc=True)
    cutoff24 = now - timedelta(hours=24)
    avg_sents = {}
    for c in COINS:
        recent = full[(full.Coin == c) & (full.Timestamp >= cutoff24)]
        avg_sents[c] = recent.Sentiment.mean() if not recent.empty else 0.0

    preds = predict_prices(avg_sents)

    # 5) Log predictions
    ensure_pred_log()
    log = load_json(PRED_LOG_JSON)
    for coin, p in preds.items():
        log[coin].append({
            "timestamp": ts_iso,
            "predicted": p
        })
    save_json(log, PRED_LOG_JSON)

    # 6) Hourly Telegram Alert
    alert = load_json(ALERT_LOG_JSON)
    last_alert = alert.get("last_alert")
    send_alert = True
    if last_alert:
        prev = datetime.fromisoformat(last_alert)
        send_alert = (now - prev >= timedelta(hours=1))

    if send_alert:
        # Sentiment
        lines = ["⏰ Hourly Sentiment & Forecast", "", "Sentiment (last hr)"]
        for c, s in avg_sents.items():
            lines.append(f"{c}: {s:+.2f}")

        # 24h Prediction Accuracy
        log = load_json(PRED_LOG_JSON)
        lines.append("", "24h Prediction Acc")
        for c in COINS:
            hist_entries = [e for e in log[c] if 'accurate' in e]
            acc = (sum(e['accurate'] for e in hist_entries) / len(hist_entries) * 100) \
                  if hist_entries else 0.0
            lines.append(f"{c}: {round(acc)}%")

        # Next‐Hour Forecast
        lines.append("", "Next Hour Forecast")
        current = fetch_prices(COINS).set_index("Coin")["PriceUSD"].to_dict()
        t1 = (now + timedelta(hours=1)).strftime("%H:%M UTC")
        for c, p in preds.items():
            curr = current.get(c, 0.0)
            pct  = (p - curr) / curr * 100 if curr else 0.0
            arrow = "↑" if pct >= 0 else "↓"
            lines.append(f"{c} by {t1}: ${p:,.2f} ({arrow}{abs(pct):.1f}%)")

        send_telegram_message("\n".join(lines))
        alert['last_alert'] = ts_iso
        save_json(alert, ALERT_LOG_JSON)
        print("✅ Telegram alert sent.")

    # 7) Back‐fill actuals & auto‐push
    update_predictions_with_actuals()
    auto_push.auto_push()

    # 8) Show last commit files
    try:
        files = subprocess.check_output(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
            text=True
        ).splitlines()
        print("✅ Files updated in last commit:")
        for f in files:
            print(f" - {f}")
    except:
        pass

if __name__ == "__main__":
    main()
