# train_price_predictor.py
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import classification_report

MODEL_PATH = "price_predictor.pkl"
HIST_CSV    = "sentiment_history.csv"


def train_and_save():
    # load your sentiment+price history
    df = pd.read_csv(HIST_CSV, parse_dates=["Timestamp"] )

    # pivot to get one row per timestamp, one column per Coin's sentiment
    pivot = df.pivot_table(
        index="Timestamp",
        columns="Coin",
        values="Sentiment",
    ).dropna()

    # next‐hour “up or down” label per coin
    shifted = pivot.shift(-1).dropna()
    X = pivot.loc[shifted.index].values
    y = (shifted.values > pivot.loc[shifted.index].values).astype(int)

    # wrap logistic regression for multi-output
    base = LogisticRegression(max_iter=1000)
    clf = MultiOutputClassifier(base)
    clf.fit(X, y)

    # save model
    joblib.dump(clf, MODEL_PATH)

    # report performance
    y_pred = clf.predict(X)
    print(classification_report(y, y_pred, target_names=["down/flat","up"]))


def predict_prices(current_prices: dict) -> dict:
    """
    Given a dict of {coin: current_price}, returns {coin: predicted_price}.
    We take each coin’s **latest** sentiment from HISTORY,
    use the saved model to predict up/down, then
    assume a ±1% move for demonstration.
    """
    clf = joblib.load(MODEL_PATH)

    # fetch last sentiment per coin
    hist = pd.read_csv(HIST_CSV, parse_dates=["Timestamp"])
    last_sent = hist.groupby("Coin")["Sentiment"].last().to_dict()

    preds = {}
    for coin, price in current_prices.items():
        s = last_sent.get(coin, 0.0)
        # predict: clf expects a row of length equal to number of coins
        # so we need to build a vector matching training ordering
        # here we assume same order as COINS list
        vec = [ last_sent.get(c, 0.0) for c in pivot.columns ]  # pivot.columns stored order
        direction = clf.predict([vec])[0][list(pivot.columns).index(coin)]
        factor = 1.01 if direction == 1 else 0.99
        preds[coin] = price * factor
    return preds


if __name__ == "__main__":
    train_and_save()
