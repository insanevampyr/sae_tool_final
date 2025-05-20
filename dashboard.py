import streamlit as st
import pandas as pd
import numpy as np
import json
import joblib
from datetime import datetime, timedelta
import os

# -------- CONFIG ---------
COINS = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]

BASE_DIR = os.path.dirname(__file__)
HIST_CSV = os.path.join(BASE_DIR, "sentiment_history.csv")
CURR_CSV = os.path.join(BASE_DIR, "sentiment_output.csv")
BTC_CSV = os.path.join(BASE_DIR, "btc_history.csv")
PRED_LOG = os.path.join(BASE_DIR, "prediction_log.json")
MODEL_PATH = os.path.join(BASE_DIR, "price_predictor.pkl")

st.set_page_config(page_title="AlphaPulse Dashboard", layout="wide")

# -------- HELPERS ---------
def load_sentiment_history():
    df = pd.read_csv(HIST_CSV)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["Timestamp", "Coin", "Sentiment"])
    return df

def load_sentiment_output():
    df = pd.read_csv(CURR_CSV)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    return df

def load_btc_history():
    try:
        df = pd.read_csv(BTC_CSV)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()

def load_prediction_log():
    try:
        with open(PRED_LOG, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def load_model():
    try:
        model, coins = joblib.load(MODEL_PATH)
        return model, coins
    except Exception:
        return None, None

def get_last_24h_sentiment(df):
    now = pd.Timestamp.utcnow()
    day_ago = now - pd.Timedelta(hours=24)
    return (
        df[df["Timestamp"] >= day_ago]
        .groupby("Coin")["Sentiment"]
        .mean()
        .reindex(COINS)
        .round(4)
        .fillna("N/A")
    )

def get_next_hour_predictions(df):
    now = pd.Timestamp.utcnow()
    # Find most recent sentiment per coin
    recents = []
    for coin in COINS:
        coin_df = df[df["Coin"] == coin].sort_values("Timestamp")
        if not coin_df.empty:
            recents.append(coin_df.iloc[-1]["Sentiment"])
        else:
            recents.append(0)
    return recents

# -------- MAIN UI ---------

st.title("AlphaPulse Crypto Dashboard")
st.markdown("**Live crypto sentiment & price tracking with ML predictions**")

tabs = st.tabs(["Sentiment Summary (24h)", "Trends Over Time", "Next Hour Predictions"])

## --- Sentiment Summary Tab ---
with tabs[0]:
    st.subheader("Sentiment Summary (Last 24h Average per Coin)")
    hist_df = load_sentiment_history()
    last24 = get_last_24h_sentiment(hist_df)
    st.table(last24.rename("24h Avg Sentiment"))

    # Current Price & Sentiment (from latest row in sentiment_output)
    st.markdown("---")
    curr_df = load_sentiment_output()
    latest = curr_df.groupby("Coin").apply(lambda x: x.sort_values("Timestamp").iloc[-1])
    st.subheader("Current Sentiment & Price")
    st.dataframe(latest[["Coin", "Sentiment", "PriceUSD", "Timestamp"]].reset_index(drop=True), use_container_width=True)

## --- Trends Over Time Tab ---
with tabs[1]:
    st.subheader("Trends Over Time: Price vs. Sentiment")
    coin = st.selectbox("Select Coin:", COINS)
    # Merge price & sentiment history for selected coin
    sent_hist = hist_df[hist_df["Coin"] == coin].sort_values("Timestamp")
    btc_hist = load_btc_history()
    if not sent_hist.empty and not btc_hist.empty:
        df_merged = sent_hist.set_index("Timestamp").join(
            btc_hist.set_index("Timestamp")[["PriceUSD"]], how="inner", rsuffix="_price"
        ).reset_index()
        # Plot (zoom: last 7 days)
        plot_df = df_merged[df_merged["Timestamp"] > (df_merged["Timestamp"].max() - pd.Timedelta(days=7))]
        st.line_chart(
            plot_df.set_index("Timestamp")[["Sentiment", "PriceUSD"]],
            use_container_width=True
        )
        st.caption("Overlay: Blue=Sentiment (scaled), Orange=Price")
    else:
        st.warning("Not enough data for this coin or BTC price history.")

## --- Next Hour Predictions Tab ---
with tabs[2]:
    st.subheader("Next Hour Price Predictions (ML Model)")
    model, coins = load_model()
    if model is not None:
        # Get latest sentiment for each coin for prediction
        curr_df = load_sentiment_output()
        sents = get_next_hour_predictions(curr_df)
        sents_np = np.array(sents).reshape(-1, 1)
        preds = model.predict(sents_np)
        pred_df = pd.DataFrame({
            "Coin": COINS,
            "Latest Sentiment": np.round(sents, 4),
            "Predicted Next Price": np.round(preds, 3)
        })
        st.dataframe(pred_df, use_container_width=True)
    else:
        st.warning("Prediction model not available. Run `train_price_predictor.py` to train.")

    # Show last predictions from log
    st.markdown("---")
    st.markdown("#### Last Predictions Log")
    pred_log = load_prediction_log()
    pred_rows = []
    for coin in COINS:
        if coin in pred_log and len(pred_log[coin]) > 0:
            entry = pred_log[coin][-1]
            pred_rows.append({
                "Coin": coin,
                "Timestamp": entry.get("timestamp"),
                "Predicted": entry.get("predicted"),
                "Actual": entry.get("actual", "N/A"),
                "Diff %": entry.get("diff_pct", "N/A"),
                "Accurate?": entry.get("accurate", "N/A"),
            })
    if pred_rows:
        st.dataframe(pd.DataFrame(pred_rows), use_container_width=True)
    else:
        st.info("No predictions logged yet.")

st.markdown("---")
st.caption("AlphaPulse Dashboard - Live Data View - Powered by Streamlit")

