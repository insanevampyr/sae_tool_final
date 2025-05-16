#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()

import os, csv, json, subprocess
from datetime import datetime, timezone, timedelta
import pandas as pd

from reddit_fetch      import fetch_reddit_posts
from rss_fetch         import fetch_rss_articles
from analyze_sentiment import analyze_sentiment
from fetch_prices      import fetch_prices
from send_telegram     import send_telegram_message
import auto_push

# ─── CONFIG ─────────────────────────────────────────────────────────────────
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
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_json(obj, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2)


def dedupe_csv(path, subset):
    df = pd.read_csv(path)
    df.drop_duplicates(subset=subset, keep='last', inplace=True)
    df.to_csv(path, index=False)


def ensure_pred_log():
    if not os.path.exists(PRED_LOG_JSON):
        init = {c: [] for c in COINS}
        save_json(init, PRED_LOG_JSON)


def update_predictions_with_actuals():
    log = load_json(PRED_LOG_JSON)
    hist = pd.read_csv(HIST_CSV)
    # parse ISO8601 timestamps
    hist['Timestamp'] = pd.to_datetime(
        hist['Timestamp'], format='ISO8601', utc=True, errors='coerce'
    )

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
                pct = abs(e['predicted'] - actual) / actual * 100 if actual else None
                e['actual'] = round(actual, 2)
                e['diff_pct'] = round(pct, 2) if pct is not None else None
                e['accurate'] = (pct is not None and pct <= TOL_PCT)
                changed = True

    if changed:
        save_json(log, PRED_LOG_JSON)

# ─── MAIN ───────────────────────────────────────────────────────────────────
def main():
    now = datetime.now(timezone.utc)
    ts_iso = now.isoformat()

    # 1) Scrape & analyze
    rows = []
    for coin in COINS:
        for post in fetch_reddit_posts('CryptoCurrency', coin, 5):
            s = analyze_sentiment(post['text'])
            rows.append({
                'Timestamp': ts_iso,
                'Coin': coin,
                'Source': 'Reddit',
                'Text': post['text'],
                'Sentiment': s
            })
        for art in fetch_rss_articles(coin, 5):
            s = analyze_sentiment(art['text'])
            rows.append({
                'Timestamp': ts_iso,
                'Coin': coin,
                'Source': 'News',
                'Text': art['text'],
                'Sentiment': s
            })

    header = not os.path.exists(OUT_CSV)
    with open(OUT_CSV, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        if header: w.writeheader()
        w.writerows(rows)
    dedupe_csv(OUT_CSV, ['Timestamp', 'Coin', 'Source', 'Text'])

    # 2) Append to history
    prices = fetch_prices()
    hist_rows = []
    df = pd.DataFrame(rows)
    for src in ('Reddit', 'News'):
        sub = df[df.Source == src]
        for coin, avg in sub.groupby('Coin')['Sentiment'].mean().items():
            hist_rows.append({
                'Timestamp': ts_iso,
                'Coin': coin,
                'Source': src,
                'Sentiment': round(avg, 4),
                'PriceUSD': prices.get(coin, 0.0),
                'SuggestedAction': (
                    '📈 Buy' if avg > 0.2 else
                    '📉 Sell' if avg < -0.2 else
                    '🤝 Hold'
                )
            })

    header2 = not os.path.exists(HIST_CSV)
    with open(HIST_CSV, 'a', newline='', encoding='utf-8') as f:
        w2 = csv.DictWriter(f, fieldnames=hist_rows[0].keys())
        if header2: w2.writeheader()
        w2.writerows(hist_rows)
    dedupe_csv(HIST_CSV, ['Timestamp', 'Coin', 'Source'])

    # 3) Hourly Telegram Alert
    alert_log = load_json(ALERT_LOG_JSON)
    last = alert_log.get('last_alert')
    send = True
    if last:
        prev = datetime.fromisoformat(last)
        send = (now - prev >= timedelta(hours=1))

    if send:
        full = pd.read_csv(HIST_CSV)
        full['Timestamp'] = pd.to_datetime(
            full['Timestamp'], format='ISO8601', utc=True, errors='coerce'
        )
        cutoff = now - timedelta(hours=1)
        recent = full[full['Timestamp'] > cutoff]

        pred_log = load_json(PRED_LOG_JSON)
        lines = [f"⏱️ Hourly update at {ts_iso} UTC"]
        for c in COINS:
            avg_s = recent[recent.Coin == c]['Sentiment'].mean() if not recent.empty else 0.0
            lastp = pred_log.get(c, [])[-1]['predicted'] if pred_log.get(c) else 0.0
            lines.append(f"{c}: Sent {avg_s:+.2f}, Pred ${lastp:.2f}")
        msg = "\n".join(lines)

        send_telegram_message(msg)
        alert_log['last_alert'] = ts_iso
        save_json(alert_log, ALERT_LOG_JSON)

    # 4) Update ML actuals & auto-push
    ensure_pred_log()
    update_predictions_with_actuals()
    auto_push.auto_push()

    # 5) Show last commit files
    try:
        files = subprocess.check_output(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
            text=True
        ).splitlines()
        print("✅ Files updated/pushed in last commit:")
        for f in files: print(" - " + f)
    except Exception as e:
        print(f"⚠️ Could not list files: {e}")

if __name__ == "__main__":
    main()
