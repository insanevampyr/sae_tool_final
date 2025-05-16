# analyze.py
from dotenv import load_dotenv
load_dotenv()

import os, csv, json, subprocess
from datetime import datetime, timezone, timedelta
import pandas as pd

from reddit_fetch       import fetch_reddit_posts
from rss_fetch          import fetch_rss_articles
from analyze_sentiment  import analyze_sentiment
from fetch_prices       import fetch_prices
from send_telegram      import send_telegram_message
import auto_push

# ─── CONFIG ─────────────────────────────────────────────────────────────────

COINS           = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
OUT_CSV         = "sentiment_output.csv"
HIST_CSV        = "sentiment_history.csv"
PRED_LOG_JSON   = "prediction_log.json"
ALERT_LOG_JSON  = "alert_log.json"
TOLERANCE_PCT   = 4  # ML accuracy threshold

# ─── UTILITY ────────────────────────────────────────────────────────────────

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_json(obj, path):
    with open(path,'w',encoding='utf-8') as f:
        json.dump(obj, f, indent=2)

def dedupe_csv(path, subset):
    df = pd.read_csv(path)
    df.drop_duplicates(subset=subset, keep='last', inplace=True)
    df.to_csv(path, index=False)

# ─── ML PREDICTION LOG ──────────────────────────────────────────────────────

def ensure_pred_log():
    if not os.path.exists(PRED_LOG_JSON):
        init = {c: [] for c in COINS}
        save_json(init, PRED_LOG_JSON)

def update_predictions_with_actuals():
    log = load_json(PRED_LOG_JSON)
    hist = pd.read_csv(HIST_CSV, parse_dates=['Timestamp'], utc=True)
    now  = datetime.now(timezone.utc)
    changed = False

    for coin, entries in log.items():
        for e in entries:
            if 'actual' in e: continue
            try:
                t0 = datetime.fromisoformat(e['timestamp'])
            except:
                continue
            if (now - t0) < timedelta(hours=1):
                continue
            sub = hist[(hist.Coin==coin)&(hist.Timestamp>t0)]
            if not sub.empty:
                actual = float(sub.iloc[0].PriceUSD)
                pct    = abs(e['predicted']-actual)/actual*100 if actual else None
                e['actual']   = round(actual,2)
                e['diff_pct'] = round(pct,2) if pct is not None else None
                e['accurate'] = pct is not None and pct <= TOLERANCE_PCT
                changed = True

    if changed:
        save_json(log, PRED_LOG_JSON)

# ─── MAIN RUN ───────────────────────────────────────────────────────────────

def main():
    now    = datetime.now(timezone.utc)
    ts_iso = now.isoformat()

    # 1) Gather & analyze
    rows = []
    for coin in COINS:
        # Reddit
        for post in fetch_reddit_posts('CryptoCurrency', coin, 5):
            s = analyze_sentiment(post['text'])
            rows.append({
                'Timestamp': ts_iso, 'Coin': coin,
                'Source': 'Reddit',
                'Text':   post['text'],
                'Sentiment': s,
                'Action':    '📈 Buy' if s>0.2 else '📉 Sell' if s<-0.2 else '🤝 Hold',
                'Link':      post.get('url','')
            })
        # News RSS
        for art in fetch_rss_articles(coin,5):
            s = analyze_sentiment(art['text'])
            rows.append({
                'Timestamp': ts_iso, 'Coin': coin,
                'Source': 'News',
                'Text':   art['text'],
                'Sentiment': s,
                'Action':    '📈 Buy' if s>0.2 else '📉 Sell' if s<-0.2 else '🤝 Hold',
                'Link':      art.get('link','')
            })

    # 2) Append raw output & dedupe
    os.makedirs(os.path.dirname(OUT_CSV) or ".", exist_ok=True)
    header = not os.path.exists(OUT_CSV)
    with open(OUT_CSV,'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        if header: w.writeheader()
        w.writerows(rows)
    dedupe_csv(OUT_CSV, ['Timestamp','Coin','Source','Text'])

    # 3) Build summary history
    prices = fetch_prices()
    hist_rows = []
    df = pd.DataFrame(rows)
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

    header = not os.path.exists(HIST_CSV)
    with open(HIST_CSV,'a', newline='', encoding='utf-8') as f:
        w2 = csv.DictWriter(f, fieldnames=hist_rows[0].keys())
        if header: w2.writeheader()
        w2.writerows(hist_rows)
    dedupe_csv(HIST_CSV, ['Timestamp','Coin','Source'])

    # 4) Hourly Telegram alert
    alert_log = load_json(ALERT_LOG_JSON)
    last_alert = alert_log.get('last_alert')
    send_alert = False

    if last_alert:
        try:
            dt0 = datetime.fromisoformat(last_alert)
            if now - dt0 >= timedelta(hours=1):
                send_alert = True
        except:
            send_alert = True
    else:
        send_alert = True

    if send_alert:
        full = pd.read_csv(HIST_CSV, parse_dates=['Timestamp'], utc=True)
        cutoff = now - timedelta(hours=1)
        recent = full[full.Timestamp>cutoff]

        pred_log = load_json(PRED_LOG_JSON)
        msg_lines = [f"⏱️ Hourly update at {ts_iso} UTC"]
        for c in COINS:
            avg = recent[recent.Coin==c]['Sentiment'].mean()
            pred = pred_log.get(c, [])[-1]['predicted'] if pred_log.get(c) else 0
            msg_lines.append(f"{c}: Sent {avg:+.2f}, Pred ${pred:.2f}")
        send_telegram_message("\n".join(msg_lines))
        alert_log['last_alert'] = ts_iso
        save_json(alert_log, ALERT_LOG_JSON)

    # 5) Append next‐hour “prediction” to log
    ensure_pred_log()
    plog = load_json(PRED_LOG_JSON)
    for c in COINS:
        plog.setdefault(c,[]).append({'timestamp':ts_iso,'predicted':prices.get(c,0)})
    save_json(plog, PRED_LOG_JSON)

    # 6) Backfill actuals & push
    update_predictions_with_actuals()
    try:
        auto_push.auto_push()
    except Exception:
        # swallow any git errors (especially on Cloud)
        pass

    # 7) Print final status
    print("✅ analyze.py complete.")

if __name__=="__main__":
    main()
