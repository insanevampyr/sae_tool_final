import streamlit as st
import pandas as pd
import numpy as np
import json
import joblib
import os
from datetime import datetime, timedelta

# CONFIG
COINS = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
SENTIMENT_CSV = "sentiment_history.csv"
PREDICTION_LOG = "prediction_log.json"
MODEL_PATH = "price_predictor.pkl"
BTC_HISTORY_CSV = "btc_history.csv"
SENTIMENT_OUTPUT = "sentiment_output.csv"

st.set_page_config(page_title="Crypto Sentiment Dashboard", layout="wide")
st.markdown("<h1 style='text-align: center; color: #3B82F6;'>Crypto Sentiment & Price Dashboard</h1>", unsafe_allow_html=True)

# Helper to read data
@st.cache_data(show_spinner=False)
def load_sentiment_history():
    df = pd.read_csv(SENTIMENT_CSV)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["Timestamp", "Coin", "Sentiment", "PriceUSD"])
    return df

@st.cache_data(show_spinner=False)
def load_sentiment_output():
    df = pd.read_csv(SENTIMENT_OUTPUT)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    return df

@st.cache_data(show_spinner=False)
def load_btc_history():
    df = pd.read_csv(BTC_HISTORY_CSV)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    return df

def load_prediction_log():
    if not os.path.exists(PREDICTION_LOG):
        return {}
    with open(PREDICTION_LOG, "r") as f:
        return json.load(f)

def load_model():
    return joblib.load(MODEL_PATH)

# Sidebar
st.sidebar.header("Coins")
selected_coin = st.sidebar.selectbox("Select Coin", COINS)

# Main Tabs
tabs = st.tabs(["Sentiment Summary", "Trends Over Time", "Next Hour Predictions"])

# Load Data
sentiment_df = load_sentiment_history()
sentiment_output = load_sentiment_output()
btc_history = load_btc_history()
pred_log = load_prediction_log()

### Sentiment Summary (Tab 1)
with tabs[0]:
    st.subheader("Sentiment Summary (Last 24h Avg per Coin)")
    cutoff = pd.Timestamp.utcnow() - pd.Timedelta("24h")
    recent = sentiment_df[sentiment_df["Timestamp"] > cutoff]
    summary = (
        recent.groupby("Coin")["Sentiment"].mean().reindex(COINS)
        .round(3)
        .reset_index()
        .rename(columns={"Sentiment": "24h Avg Sentiment"})
    )
    st.dataframe(summary, hide_index=True, use_container_width=True)

### Trends Over Time (Tab 2)
with tabs[1]:
    st.subheader(f"Trends Over Time — {selected_coin}")
    coin_df = sentiment_df[sentiment_df["Coin"] == selected_coin].sort_values("Timestamp")
    # Last 48h for more zoom
    min_time = pd.Timestamp.utcnow() - pd.Timedelta("48h")
    coin_df = coin_df[coin_df["Timestamp"] > min_time]

    # Plot Price vs Sentiment overlay
    import matplotlib.pyplot as plt
    fig, ax1 = plt.subplots(figsize=(10, 4))
    ax2 = ax1.twinx()
    ax1.plot(coin_df["Timestamp"], coin_df["PriceUSD"], 'b-', label='Price', linewidth=2)
    ax2.plot(coin_df["Timestamp"], coin_df["Sentiment"], 'g-', label='Sentiment', alpha=0.5)
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Price (USD)", color='b')
    ax2.set_ylabel("Sentiment", color='g')
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    st.caption("Scroll horizontally or zoom with the chart's toolbar for closer analysis.")

### Next Hour Predictions (Tab 3)
with tabs[2]:
    st.subheader("Next Hour Price Predictions (Live)")

    # Show latest sentiment for each coin
    latest = (
        sentiment_output.groupby("Coin")
        .apply(lambda x: x.sort_values("Timestamp").iloc[-1])
        .reset_index(drop=True)
    )
    st.markdown("#### Current Sentiment (live)")
    st.dataframe(latest[["Coin", "Sentiment"]], hide_index=True)

    # Predict prices
    avg_sents = [latest[latest["Coin"] == c]["Sentiment"].values[0] for c in COINS]
    model, _ = load_model()
    preds = model.predict(np.array(avg_sents).reshape(-1, 1))
    pred_df = pd.DataFrame({
        "Coin": COINS,
        "Predicted Price (Next Hour)": [f"${x:,.2f}" for x in preds]
    })
    st.markdown("#### Predicted Next-Hour Prices")
    st.dataframe(pred_df, hide_index=True)

    # Show recent prediction accuracy
    pred_log = load_prediction_log()
    st.markdown("#### Recent Prediction Accuracy")
    for coin in COINS:
        entries = pred_log.get(coin, [])
        acc = [x for x in entries if x.get("accurate") is True]
        if acc:
            st.write(f"**{coin}:** {len(acc)} recent accurate predictions.")
        else:
            st.write(f"**{coin}:** No recent accurate predictions logged.")
            