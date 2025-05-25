#!/usr/bin/env python3
# train_price_predictor.py

import os
import pandas as pd
import joblib
from dateutil import parser
import datetime
from sklearn.ensemble import RandomForestRegressor

# ─── CONFIG ────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(__file__)
HIST_CSV    = os.path.join(BASE_DIR, "sentiment_history.csv")
MODEL_PATH  = os.path.join(BASE_DIR, "price_predictor.pkl")
COINS       = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
HORIZON_HRS = 1  # predict 1 hour ahead

def train_and_save():
    # 1) Load & parse history
    df = pd.read_csv(HIST_CSV)
    # parse timestamps, drop tzinfo so everything is tz-naive UTC
    df["Timestamp"] = (
        pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
          .dt.tz_convert(None)
    )
    df = df.dropna(subset=["Timestamp", "PriceUSD", "Sentiment"])

    # 2) Build training records
    records = []
    for coin in COINS:
        sub = (
            df[df["Coin"] == coin]
              .sort_values("Timestamp")
              .reset_index(drop=True)
        )
        # shift price by HORIZON_HRS
        sub["TargetPrice"] = sub["PriceUSD"].shift(-HORIZON_HRS)
        valid = sub.dropna(subset=["TargetPrice"])
        for _, row in valid.iterrows():
            records.append({
                "AvgSentiment": row["Sentiment"],
                "TargetPrice":  row["TargetPrice"]
            })

    train_df = pd.DataFrame(records)
    X = train_df[["AvgSentiment"]]
    y = train_df["TargetPrice"]

    # 3) Train
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)

    # 4) Persist
    joblib.dump((model, COINS), MODEL_PATH)
    print(f"✅ Trained and saved model to {MODEL_PATH}")

def predict_prices(avg_sents):
    """
    avg_sents: list of floats in same order as COINS.
    Returns numpy array of predicted next-hour prices.
    """
    model, coins = joblib.load(MODEL_PATH)
    dfX = pd.DataFrame(avg_sents, columns=["AvgSentiment"])
    return model.predict(dfX)

if __name__ == "__main__":
    train_and_save()
