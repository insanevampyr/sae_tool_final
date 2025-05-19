#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()

import os, csv, json, subprocess
from datetime import datetime, timedelta, timezone
import pandas as pd
from dateutil import parser

from reddit_fetch      import fetch_reddit_posts
from rss_fetch         import fetch_rss_articles
from analyze_sentiment import analyze_sentiment
from fetch_prices      import fetch_prices
from send_telegram     import send_telegram_message
import auto_push

# ─── CONFIG ─────────────────────────────────────────────────────────────
COINS          = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
OUT_CSV        = "sentiment_output.csv"
HIST_CSV       = "sentiment_history.csv"
PRED_LOG_JSON  = "prediction_log.json"
ALERT_LOG_JSON = "alert_log.json"
TOL_PCT        = 4  # ML accuracy threshold (%)

# ─── HELPERS ─────────────────────────────────────────────────────────────
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
    # only keep subset columns that exist
    cols = [c for c in subset if c in df.columns]
    if cols:
        df.drop_duplicates(subset=cols, keep='last', inplace=True)
        df.to_csv(path, index=False)


def ensure_pred_log():
    if not os.path.exists(PRED_LOG_JSON):
        init = {c: [] for c in COINS}
        save_json(init, PRED_LOG_JSON)


def update_predictions_with_actuals():
    log = load_json(PRED_LOG_JSON)
    hist = pd.read_csv(HIST_CSV)
    hist['Timestamp'] = hist['Timestamp'].apply(parser.isoparse).apply(lambda dt: dt.replace(tzinfo=None))

    now = datetime.utcnow()
    changed = False

    for coin, entries in log.items():
        for e in entries:
            # skip entries without a prediction
            if 'predicted' not in e:
                continue
            # skip if already filled
            if 'actual' in e:
                continue

            t0 = parser.isoparse(e['timestamp']).replace(tzinfo=None)
            # not yet hour past prediction
            if now - t0 < timedelta(hours=1):
                continue

            sub = hist[(hist.Coin == coin) & (hist.Timestamp > t0)]
            if not sub.empty:
                actual = float(sub.iloc[0].PriceUSD)
                pct = abs(e['predicted'] - actual) / actual * 100 if actual else None
                e['actual']   = round(actual, 2)
                e['diff_pct'] = round(pct, 2) if pct is not None else None
                e['accurate'] = (pct is not None and pct <= TOL_PCT)
                changed = True

    if changed:
        save_json(log, PRED_LOG_JSON)

# ─── MAIN ─────────────────────────────────────────────────────────────────
def main():
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    ts_iso = now.isoformat()

    # 1) Scrape & analyze sentiment
    rows = []
    for coin in COINS:
        reddit_posts = fetch_reddit_posts([coin])[:5]
        for post in reddit_posts:
            s = analyze_sentiment(post['Text'])
            rows.append({
                'Timestamp': ts_iso,
                'Coin': coin,
                'Source': 'Reddit',
                'Text': post['Text'],
                'Sentiment': s
            })

        rss_articles = fetch_rss_articles(coin)[:5]
        for art in rss_articles:
            s = analyze_sentiment(art['text'])
            rows.append({
                'Timestamp': ts_iso,
                'Coin': coin,
                'Source': 'News',
                'Text': art['text'],
                'Sentiment': s
            })

    # Write raw output
    header1 = not os.path.exists(OUT_CSV)
    with open(OUT_CSV, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        if header1: w.writeheader()
        w.writerows(rows)
    dedupe_csv(OUT_CSV, ['Timestamp', 'Coin', 'Source', 'Text'])

    # 2) Append to history with SuggestedAction
    prices = fetch_prices(COINS).set_index('Coin')['PriceUSD'].to_dict()
    hist_rows = []
    df = pd.DataFrame(rows)
    for src in ('Reddit', 'News'):
        sub = df[df.Source == src]
        for coin, avg in sub.groupby('Coin')['Sentiment'].mean().items():
            price = float(prices.get(coin, 0.0))
            action = (
                '📈 Buy'  if avg >  0.2 else
                '📉 Sell' if avg < -0.2 else
                '🤝 Hold'
            )
            hist_rows.append({
                'Timestamp':       ts_iso,
                'Coin':            coin,
                'Source':          src,
                'Sentiment':       round(avg, 4),
                'PriceUSD':        round(price, 2),
                'SuggestedAction': action
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
    send  = True
    if last:
        prev = parser.isoparse(last).replace(tzinfo=None)
        send = (now.replace(tzinfo=None) - prev) >= timedelta(hours=1)
    if send:
        full = pd.read_csv(HIST_CSV)
        full['Timestamp'] = full['Timestamp'].apply(parser.isoparse).apply(lambda dt: dt.replace(tzinfo=None))
        cutoff = now.replace(tzinfo=None) - timedelta(hours=1)
        recent = full[full['Timestamp'] > cutoff]

        lines = [f"⏱️ Hourly update at {ts_iso}"]
        pred_log = load_json(PRED_LOG_JSON)
        for c in COINS:
            avg_s = recent[recent.Coin == c]['Sentiment'].mean() if not recent.empty else 0.0
            lastp_list = pred_log.get(c, [])
            lastp = lastp_list[-1]['predicted'] if lastp_list else 0.0
            lines.append(f"{c}: Sent {avg_s:+.2f}, Pred ${lastp:.2f}")
        send_telegram_message("\n".join(lines))
        alert_log['last_alert'] = ts_iso
        save_json(alert_log, ALERT_LOG_JSON)

    # 4) Prediction-log maintenance & auto-push
    ensure_pred_log()
    update_predictions_with_actuals()
    auto_push.auto_push()

    # 5) Commit-diff helper
    try:
        files = subprocess.check_output([
            'git','diff-tree','--no-commit-id','--name-only','-r','HEAD'
        ], text=True).splitlines()
        print("✅ Files updated in last commit:")
        for f in files: print(" - ", f)
    except Exception as e:
        print("⚠️ Could not list commit files:", e)

if __name__ == "__main__":
    main()
