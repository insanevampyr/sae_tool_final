#!/usr/bin/env python3
# analyze.py

import os, csv, json, subprocess
from datetime import datetime, timezone, timedelta
import pandas as pd
from dateutil import parser
from dotenv import load_dotenv

from reddit_fetch      import fetch_reddit_posts
from rss_fetch         import fetch_rss_articles
from analyze_sentiment import analyze_sentiment
from fetch_prices      import fetch_prices
from send_telegram     import send_telegram_message
import auto_push

# ─── CONFIG ─────────────────────────────────────────────────────────────
load_dotenv()
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
            return json.load(open(path, "r", encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}

def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def dedupe_csv(path, subset):
    """
    Drop duplicates in `path` based on whichever of `subset` actually exist.
    """
    if not os.path.exists(path):
        return
    df = pd.read_csv(path)
    valid = [col for col in subset if col in df.columns]
    if valid:
        df.drop_duplicates(subset=valid, keep="last", inplace=True)
        df.to_csv(path, index=False)

def ensure_pred_log():
    if not os.path.exists(PRED_LOG_JSON):
        init = {c: [] for c in COINS}
        save_json(init, PRED_LOG_JSON)

def update_predictions_with_actuals():
    log = load_json(PRED_LOG_JSON)
    hist = pd.read_csv(HIST_CSV)
    # parse and drop tz info for comparison
    hist["Timestamp"] = (
        hist["Timestamp"]
        .apply(parser.isoparse)
        .apply(lambda dt: dt.replace(tzinfo=None))
    )

    now = datetime.utcnow()
    changed = False

    for coin, entries in log.items():
        for e in entries:
            if "actual" in e or "predicted" not in e:
                continue
            t0 = parser.isoparse(e["timestamp"]).replace(tzinfo=None)
            if now - t0 < timedelta(hours=1):
                continue
            sub = hist[(hist.Coin == coin) & (hist.Timestamp > t0)]
            if not sub.empty:
                actual = float(sub.iloc[0].PriceUSD)
                pct = abs(e["predicted"] - actual) / actual * 100 if actual else None
                e["actual"]   = round(actual, 2)
                e["diff_pct"] = round(pct, 2) if pct is not None else None
                e["accurate"] = (pct is not None and pct <= TOL_PCT)
                changed = True

    if changed:
        save_json(log, PRED_LOG_JSON)

# ─── MAIN ─────────────────────────────────────────────────────────────────
def main():
    now    = datetime.utcnow().replace(tzinfo=timezone.utc)
    ts_iso = now.isoformat()

    # 1) Scrape & analyze
    rows = []
    for coin in COINS:
        for post in fetch_reddit_posts([coin])[:5]:
            text = post["Text"]
            s    = analyze_sentiment(text)
            rows.append({
                "Timestamp": ts_iso, "Coin": coin,
                "Source": "Reddit",    "Text": text,
                "Sentiment": s
            })
        for art in fetch_rss_articles(coin)[:5]:
            text = art.get("text", "")
            s    = analyze_sentiment(text)
            rows.append({
                "Timestamp": ts_iso, "Coin": coin,
                "Source": "News",      "Text": text,
                "Sentiment": s
            })

    # Write raw sentiment_output.csv
    header1 = not os.path.exists(OUT_CSV)
    with open(OUT_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        if header1: w.writeheader()
        w.writerows(rows)
    dedupe_csv(OUT_CSV, ["Timestamp","Coin","Source","Text"])

    # 2) Append to history with SuggestedAction
    prices = fetch_prices(COINS).set_index("Coin")["PriceUSD"].to_dict()
    hist_rows = []
    df = pd.DataFrame(rows)
    for src in ("Reddit","News"):
        sub = df[df.Source == src]
        for coin, avg in sub.groupby("Coin")["Sentiment"].mean().items():
            price  = float(prices.get(coin, 0.0))
            action = (
                "📈 Buy"  if avg >  0.2 else
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
    dedupe_csv(HIST_CSV, ["Timestamp","Coin","Source"])

    # 3) Hourly Telegram Alert (formatted as requested)
    alert = load_json(ALERT_LOG_JSON)
    last = alert.get("last_alert")
    last_dt = parser.isoparse(last) if last else None
    if not last_dt or (now - last_dt >= timedelta(hours=1)):
        full = pd.read_csv(HIST_CSV)
        full["Timestamp"] = full["Timestamp"].apply(parser.isoparse)
        cutoff = now - timedelta(hours=1)

        ensure_pred_log()
        update_predictions_with_actuals()
        pred_log = load_json(PRED_LOG_JSON)

        lines = ["⏰ Hourly Sentiment & Forecast", ""]
        lines.append("Sentiment (last hr)")
        for c in COINS:
            vals = full[(full.Coin==c)&(full.Timestamp>cutoff)]["Sentiment"]
            avg_s = vals.mean() if not vals.empty else 0.0
            lines.append(f"{c}: {avg_s:+.2f}")
        lines.append("")
        lines.append("24h Prediction Acc")
        acc_cut = now - timedelta(hours=24)
        for c in COINS:
            ent = [e for e in pred_log.get(c,[]) if parser.isoparse(e["timestamp"])>=acc_cut and "accurate" in e]
            pct = int(100*sum(e["accurate"] for e in ent)/len(ent)) if ent else 0
            lines.append(f"{c}: {pct}%")
        lines.append("")
        lines.append("Next Hour Forecast")
        nxt    = (now + timedelta(hours=1)).strftime("%H:%M UTC")
        for c in COINS:
            e = pred_log.get(c, [])[0]
            diff = e.get("diff_pct",0)
            arrow = "↑" if diff>=0 else "↓"
            lines.append(f"{c} by {nxt}: ${e['predicted']:.2f} ({arrow}{abs(diff):.1f}%)")

        send_telegram_message("\n".join(lines))
        alert["last_alert"] = ts_iso
        save_json(alert, ALERT_LOG_JSON)

    # 4) Final maintenance
    update_predictions_with_actuals()
    auto_push.auto_push()

    # 5) Commit‐diff helper
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
