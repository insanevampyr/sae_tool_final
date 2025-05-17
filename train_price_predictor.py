# train_price_predictor.py

import pandas as pd
import numpy as np
from sklearn.multioutput import MultiOutputClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

# ─── CONFIG ────────────────────────────────────────────────────────────────
HIST_CSV = "sentiment_history.csv"
WINDOW_HRS = 1            # how far back to look for features
TARGET_HRS = 1            # how far ahead to predict price movement
MODEL_FILE = "price_predictor.pkl"
COINS = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]

def load_features_and_targets():
    df = pd.read_csv(HIST_CSV, parse_dates=["Timestamp"])
    df = df.sort_values("Timestamp").set_index("Timestamp")
    X, ys = [], {coin: [] for coin in COINS}
    for t in range(WINDOW_HRS, len(df)-TARGET_HRS):
        window = df.iloc[t-WINDOW_HRS:t]
        future = df.iloc[t+TARGET_HRS]["PriceUSD"]
        now = df.iloc[t]["PriceUSD"]
        features = window["Sentiment"].values  # shape=(WINDOW_HRS,)
        X.append(features)
        for i, coin in enumerate(COINS):
            # if price up over next hour → 1 else 0
            ys[coin].append(int(future > now))
    X = np.stack(X)
    y = np.stack([ys[c] for c in COINS], axis=1)  # shape=(n_samples,4)
    return X, y

def train_and_save():
    X, y = load_features_and_targets()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = MultiOutputClassifier(LogisticRegression(max_iter=500))
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)

    # print per‐coin reports
    for idx, coin in enumerate(COINS):
        print(f"\n=== {coin} ===")
        print(classification_report(
            y_test[:, idx],
            y_pred[:, idx],
            labels=[0,1],
            target_names=["down/flat","up"]
        ))

    joblib.dump(clf, MODEL_FILE)
    print(f"\n💾 Model saved to {MODEL_FILE}")

if __name__ == "__main__":
    train_and_save()

import joblib
import pandas as pd

MODEL_PATH = "price_predictor.pkl"

def predict_prices(sentiment_window: pd.DataFrame) -> list[float]:
    """
    Given a DataFrame `sentiment_window` with columns ['Timestamp','AvgSentiment'],
    returns a list of predictions (0 or 1) for each row.
    """
    model = joblib.load(MODEL_PATH)
    X = sentiment_window[["AvgSentiment"]]
    return model.predict(X).tolist()
