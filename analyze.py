#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()

import os, csv, json
from datetime import datetime, timezone, timedelta
import pandas as pd

from reddit_fetch       import fetch_reddit_posts
from rss_fetch          import fetch_rss_articles
from analyze_sentiment  import analyze_sentiment
from fetch_prices       import fetch_prices
from send_telegram      import send_telegram_message
import auto_push

# ─── CONFIG ─────────────────────────────────────────────────────────────────
COINS          = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
OUT_CSV        = "sentiment_output.csv"
HIST_CSV       = "sentiment_history.csv"
PRED_LOG_JSON  = "prediction_log.json"
TOLERANCE_PCT  = 4   # ±4% error tolerance

# ─── HELPERS ─────────────────────────────────────────────────────────────────
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

def dedupe_csv(path, subset):
    df = pd.read_csv(path, parse_dates=['Timestamp'])
    df.drop_duplicates(subset=subset, keep='last', inplace=True)
    df.to_csv(path, index=False)

def ensure_pred_log():
    if not os.path.exists(PRED_LOG_JSON):
        save_json({c: [] for c in COINS}, PRED_LOG_JSON)

# ─── BACKFILL ACTUALS ────────────────────────────────────────────────────────
def update_predictions_with_actuals():
    log = load_json(PRED_LOG_JSON)
    if not os.path.exists(HIST_CSV):
        return

    hist = pd.read_csv(HIST_CSV, parse_dates=['Timestamp'])
    if hist['Timestamp'].dt.tz is None:
        hist['Timestamp'] = hist['Timestamp'].dt.tz_localize('UTC')
    now = datetime.now(timezone.utc)
    changed = False

    for coin, entries in log.items():
        for entry in entries:
            if 'actual' in entry:
                continue
            # only backfill if >1h old
            try:
                t0 = datetime.fromisoformat(entry['timestamp'])
            except ValueError:
                continue
            if now - t0 < timedelta(hours=1):
                continue

            sub = hist[(hist.Coin == coin) & (hist.Timestamp > t0)]
            if not sub.empty:
                actual = float(sub.iloc[0].PriceUSD)
                pct    = abs(entry['predicted'] - actual) / actual * 100 if actual else None
                entry['actual']   = round(actual, 2)
                entry['diff_pct'] = round(pct, 2) if pct is not None else None
                entry['accurate'] = pct is not None and pct <= TOLERANCE_PCT
                changed = True

    if changed:
        save_json(log, PRED_LOG_JSON)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    now    = datetime.now(timezone.utc)
    ts_iso = now.isoformat()

    # 1) Gather posts + articles & analyze
    rows = []
    for coin in COINS:
        # Reddit
        for post in fetch_reddit_posts('CryptoCurrency', coin, 5):
            s = analyze_sentiment(post['text'])
            rows.append({
                'Timestamp': ts_iso, 'Coin': coin,
                'Source': 'Reddit',
                'Text':   post['text'],
                'Sentiment': round(s,4),
                'Action':    '📈 Buy' if s>0.2 else '📉 Sell' if s<-0.2 else '🤝 Hold',
                'Link':      post.get('url','')
            })
        # RSS News
        for art in fetch_rss_articles(coin,5):
            s = analyze_sentiment(art['text'])
            rows.append({
                'Timestamp': ts_iso, 'Coin': coin,
                'Source': 'News',
                'Text':   art['text'],
                'Sentiment': round(s,4),
                'Action':    '📈 Buy' if s>0.2 else '📉 Sell' if s<-0.2 else '🤝 Hold',
                'Link':      art.get('link','')
            })

    # 2) Append raw output + dedupe
    os.makedirs(os.path.dirname(OUT_CSV) or ".", exist_ok=True)
    with open(OUT_CSV,'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        if os.stat(OUT_CSV).st_size == 0:
            writer.writeheader()
        writer.writerows(rows)
    dedupe_csv(OUT_CSV, ['Timestamp','Coin','Source','Text'])

    # 3) Build summary history
    prices    = fetch_prices()
    hist_rows = []
    df        = pd.DataFrame(rows)
    for src in ['Reddit','News']:
        sub = df[df.Source==src]
        for coin, avg in sub.groupby('Coin')['Sentiment'].mean().round(4).items():
            hist_rows.append({
                'Timestamp': ts_iso,
                'Coin':      coin,
                'Source':    src,
                'Sentiment': avg,
                'PriceUSD':  prices.get(coin,0),
                'SuggestedAction': '📈 Buy' if avg>0.2 else '📉 Sell' if avg<-0.2 else '🤝 Hold'
            })
    with open(HIST_CSV,'a', newline='', encoding='utf-8') as f:
        w2 = csv.DictWriter(f, fieldnames=hist_rows[0].keys())
        if os.stat(HIST_CSV).st_size == 0:
            w2.writeheader()
        w2.writerows(hist_rows)
    dedupe_csv(HIST_CSV, ['Timestamp','Coin','Source'])

    # 4) **Hourly Summary Alert**  
    #    (Assumes you run this script once an hour; will send exactly one message per run.)
    full     = pd.read_csv(HIST_CSV, parse_dates=['Timestamp'])
    if full['Timestamp'].dt.tz is None:
        full['Timestamp'] = full['Timestamp'].dt.tz_localize('UTC')
    cutoff   = now - timedelta(hours=1)
    recent   = full[full.Timestamp > cutoff]
    p_log    = load_json(PRED_LOG_JSON)
    lines    = [f"⏱️ Hourly Update at {now.strftime('%Y-%m-%d %H:%M')} UTC"]
    for c in COINS:
        avg   = recent[recent.Coin==c]['Sentiment'].mean() if not recent.empty else 0
        price = prices.get(c,0)
        pred  = p_log.get(c, [])[-1]['predicted'] if p_log.get(c) else 0
        # compute % diff relative to current price
        pct   = round((pred - price)/price*100,2) if price else 0
        arrow = "🟢" if pct>0 else "🔴" if pct<0 else "⚪️"
        lines.append(f"{c}: Sent {avg:+.2f}, Price ${price:.2f}, Pred ${pred:.2f} ({pct:+.2f}%){arrow}")
    send_telegram_message("\n".join(lines))

    # 5) Append next‐hour “predicted” prices
    ensure_pred_log()
    plog = load_json(PRED_LOG_JSON)
    for c in COINS:
        plog.setdefault(c, []).append({'timestamp':ts_iso,'predicted':prices.get(c,0)})
    save_json(plog, PRED_LOG_JSON)

    # 6) Backfill actuals & auto‐push
    update_predictions_with_actuals()
    try:
        auto_push.auto_push()
    except:
        pass

    print("✅ analyze.py complete.")

if __name__=="__main__":
    main()
