#!/usr/bin/env python3
# train_price_predictor.py

import os
import pandas as pd
import numpy as np
import joblib
from dateutil import parser
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# ─── CONFIG ────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(__file__)
HIST_CSV   = os.path.join(BASE_DIR, "sentiment_history.csv")
TARGET_HRS = 1            # how many hours ahead to label
MODEL_FILE = os.path.join(BASE_DIR, "price_predictor.pkl")
COINS      = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]


def train_and_save():
    # 1) load data
    df = pd.read_csv(HIST_CSV)
    # 2) parse ISO8601 timestamps
    df["Timestamp"] = df["Timestamp"].apply(parser.isoparse)
    df["Timestamp"] = pd.DatetimeIndex(df["Timestamp"])

    models = {}
    for coin in COINS:
        sub = df[df.Coin == coin].sort_values("Timestamp").reset_index(drop=True)
        times  = sub["Timestamp"]
        prices = sub["PriceUSD"]
        sents  = sub["Sentiment"]

        X, y = [], []
        for i, t in enumerate(times):
            cutoff = t + pd.Timedelta(hours=TARGET_HRS)
            future = times[times >= cutoff]
            if future.empty:
                continue
            j = future.index[0]
            X.append([sents.iloc[i]])
            y.append(int(prices.iloc[j] > prices.iloc[i]))

        if len(y) < 10:
            print(f"⚠️  Skipping {coin}: only {len(y)} samples")
            continue

        X_arr = np.array(X)
        y_arr = np.array(y)
        X_train, X_test, y_train, y_test = train_test_split(
            X_arr, y_arr, test_size=0.2, shuffle=False
        )

        clf = LogisticRegression(max_iter=200)
        clf.fit(X_train, y_train)
        preds = clf.predict(X_test)

        print(f"\n--- {coin} classification report ---")
        print(classification_report(y_test, preds))

        models[coin] = clf

    # 3) dump all coin‐models into one pickle
    joblib.dump(models, MODEL_FILE)
    print(f"\n✅ Trained and saved {len(models)} models to {MODEL_FILE}")


def predict_prices(sentiment_window: pd.DataFrame) -> list[int]:
    """
    sentiment_window: DataFrame with column "AvgSentiment" for one coin.
    Returns a list of 0/1 predictions matching each row.
    """
    models = joblib.load(MODEL_FILE)
    # if you want per‐coin models, index by coin name; 
    # for now just pick one since each clf is identical shape
    clf = next(iter(models.values()))
    X = sentiment_window[["AvgSentiment"]].values
    return clf.predict(X).tolist()


if __name__ == "__main__":
    train_and_save()
