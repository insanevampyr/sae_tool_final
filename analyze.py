# analyze.py
from dotenv import load_dotenv
load_dotenv()   # now os.environ will see TELEGRAM_TOKEN & TELEGRAM_CHAT_ID

import os, csv, json, subprocess
from datetime import datetime, timezone, timedelta
import pandas as pd

from analyze_sentiment import analyze_sentiment
from reddit_fetch import fetch_reddit_posts
from rss_fetch import fetch_rss_articles
from fetch_prices import fetch_prices
from send_telegram import send_telegram_message
import auto_push

# --- CONFIG ---
coins = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
output_file = "sentiment_output.csv"
history_file = "sentiment_history.csv"
ml_log_path = "prediction_log.json"
tolerance_pct = 4  # accuracy threshold in percent

# --- Helpers ---
def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def remove_duplicates(path, subset):
    df = pd.read_csv(path)
    df.drop_duplicates(subset=subset, keep='last', inplace=True)
    df.to_csv(path, index=False)

# --- Initialize ML log ---
def init_prediction_log():
    default = {coin: [] for coin in coins}
    save_json(default, ml_log_path)
    print(f"✅ Initialized {ml_log_path}")

# --- Update actuals in ML log ---
def update_predictions():
    log = load_json(ml_log_path)
    if not isinstance(log, dict):
        init_prediction_log()
        return
    if not os.path.exists(history_file):
        return

    hist = pd.read_csv(history_file)
    hist['Timestamp'] = pd.to_datetime(hist['Timestamp'], utc=True, errors='coerce')
    now = datetime.now(timezone.utc)
    changed = False

    for coin, entries in log.items():
        for entry in entries:
            if entry.get('actual') is not None:
                continue
            ts = entry.get('timestamp', '')
            try:
                t0 = datetime.fromisoformat(ts)
            except Exception:
                continue
            if now - t0 < timedelta(hours=1):
                continue
            df_sub = hist[(hist['Coin'] == coin) & (hist['Timestamp'] > t0)]
            if not df_sub.empty:
                actual = float(df_sub.iloc[0].get('PriceUSD', 0))
                pct = abs((entry.get('predicted', 0) - actual) / actual) * 100 if actual else None
                entry['actual'] = round(actual, 2)
                entry['diff_pct'] = round(pct, 2) if pct is not None else None
                entry['accurate'] = pct is not None and pct <= tolerance_pct
                changed = True
    if changed:
        save_json(log, ml_log_path)
        print(f"✅ Updated {ml_log_path} with actual prices")

# --- Main script ---
def main():
    now = datetime.now(timezone.utc)
    ts_iso = now.isoformat()

    # 1) Fetch and analyze sentiment
    rows = []
    for coin in coins:
        for p in fetch_reddit_posts('CryptoCurrency', coin, 5):
            s = analyze_sentiment(p.get('text', ''))
            rows.append({
                'Timestamp': ts_iso,
                'Coin': coin,
                'Source': 'Reddit',
                'Text': p.get('text', ''),
                'Sentiment': s,
                'Action': '📈 Buy' if s > 0.2 else '📉 Sell' if s < -0.2 else '🤝 Hold',
                'Link': p.get('url', '')
            })
    for coin in coins:
        for a in fetch_rss_articles(coin, 5):
            s = analyze_sentiment(a.get('text', ''))
            rows.append({
                'Timestamp': ts_iso,
                'Coin': coin,
                'Source': 'News',
                'Text': a.get('text', ''),
                'Sentiment': s,
                'Action': '📈 Buy' if s > 0.2 else '📉 Sell' if s < -0.2 else '🤝 Hold',
                'Link': a.get('link', '')
            })

    # 2) Write output and history
    header_out = not os.path.exists(output_file)
    with open(output_file, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        if header_out:
            w.writeheader()
        w.writerows(rows)
    remove_duplicates(output_file, ['Timestamp', 'Coin', 'Source', 'Text'])

    prices = fetch_prices()
    hist_rows = []
    df_all = pd.DataFrame(rows)
    for src in ['Reddit', 'News']:
        df_src = df_all[df_all['Source'] == src]
        if df_src.empty:
            continue
        for coin, avg in df_src.groupby('Coin')['Sentiment'].mean().round(4).items():
            hist_rows.append({
                'Timestamp': ts_iso,
                'Coin': coin,
                'Source': src,
                'Sentiment': avg,
                'PriceUSD': prices.get(coin, ''),
                'SuggestedAction': '📈 Buy' if avg > 0.2 else '📉 Sell' if avg < -0.2 else '🤝 Hold'
            })
    header_hist = not os.path.exists(history_file)
    with open(history_file, 'a', newline='', encoding='utf-8') as f:
        w2 = csv.DictWriter(f, fieldnames=hist_rows[0].keys())
        if header_hist:
            w2.writeheader()
        w2.writerows(hist_rows)
    remove_duplicates(history_file, ['Timestamp', 'Coin', 'Source'])

    # 3) Telegram alerts
    for c in coins:
        avg_val = pd.DataFrame(hist_rows).query('Coin==@c')['Sentiment'].mean()
        send_telegram_message(f"🚨 {c} avg sentiment: {avg_val:.2f}")

    # 4) Initialize or append ML predictions
    if not os.path.exists(ml_log_path):
        init_prediction_log()
    log = load_json(ml_log_path)
    for c in coins:
        log.setdefault(c, []).append({'timestamp': ts_iso, 'predicted': prices.get(c, 0)})
    save_json(log, ml_log_path)
    print(f"✅ Appended new ML predictions to {ml_log_path}")

    # 5) Update actuals and auto-push
    update_predictions()
    auto_push.auto_push()

    # 6) Print committed files
    try:
        files = subprocess.check_output(
            ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD'], text=True
        ).splitlines()
        print('✅ Files updated/pushed:')
        for fn in files:
            print(f' - {fn}')
    except Exception as e:
        print(f"⚠️ Could not list files: {e}")

if __name__ == '__main__':
    main()