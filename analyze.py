# analyze.py
from fetch_prices import fetch_prices
from train_price_predictor import predict_prices

# … after fetching sentiment_history.csv into df …
last_hour = df[df.Timestamp >= (now - pd.Timedelta(hours=1))]
sent_avg = (
    last_hour
    .groupby("Timestamp")
    .agg({"Sentiment":"mean", "PriceUSD":"last"})
    .rename(columns={"Sentiment":"AvgSentiment","PriceUSD":"CurrentPrice"})
    .reset_index()
)

# run model:
labels = predict_prices(sent_avg)

# turn labels into “predicted price” for each Timestamp:
# (here we simply add +1% if label==1, -1% if label==0)
sent_avg["PredictedPrice"] = sent_avg.apply(
    lambda row: row.CurrentPrice * (1.01 if labels.pop(0)==1 else 0.99),
    axis=1
)

# pick the very last row as “next‐hour” forecast:
fore = sent_avg.iloc[-1]
push_entry = {
    "timestamp": fore.Timestamp.isoformat(),
    "current": fore.CurrentPrice,
    "predicted": fore.PredictedPrice,
    "diff_pct": round((fore.PredictedPrice - fore.CurrentPrice)/fore.CurrentPrice*100,2),
    "accurate": None  # will be set when we compare to actual
}

# append push_entry to prediction_log.json for each coin…

from crypto_price_alerts import COINS        # your list of coins
from analyze_sentiment import get_latest_sentiment  # however you get your sentiment
from auto_push import auto_push              # your scheduling helper
from datetime import datetime, timezone
import json
import os
import pandas as pd

# ─── CONFIG ─────────────────────────────────────
HIST_CSV      = "sentiment_history.csv"
PRED_LOG_JSON = "prediction_log.json"

def update_sentiment_history():
    new = get_latest_sentiment()
    df = pd.DataFrame(new)
    df.to_csv(HIST_CSV, mode="a", header=not os.path.exists(HIST_CSV), index=False)

def update_prediction_log():
    # fetch current prices & make next‐hour predictions
    current = fetch_prices()
    preds = predict_prices(current)

    # compute last 24 h accuracy
    cutoff = datetime.now(timezone.utc).timestamp() - 24*3600
    log = []
    if os.path.exists(PRED_LOG_JSON):
        log = json.load(open(PRED_LOG_JSON, "r", encoding="utf-8"))

    # check last 24 h entries
    recent = [e for e in log if datetime.fromisoformat(e["timestamp"])\
              .replace(tzinfo=timezone.utc).timestamp() > cutoff]
    acc = sum(1 for e in recent if e.get("accurate")) / (len(recent) or 1)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "current":   current,
        "predicted": preds,
        "accuracy24h": f"{acc*100:.0f}%"
    }
    log.insert(0, entry)
    with open(PRED_LOG_JSON, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

def main():
    update_sentiment_history()
    update_prediction_log()
    print("✅ Updated sentiment_history.csv and prediction_log.json")

if __name__ == "__main__":
    main()
