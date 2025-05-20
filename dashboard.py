import streamlit as st
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from dateutil import parser

# =============== CONFIG ===============
COINS = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
HISTORY_DAYS = 7
SENTIMENT_FILE = "sentiment_history.csv"
PREDICTION_LOG = "prediction_log.json"

# =============== HELPERS ===============
@st.cache_data
def load_sentiment_history():
    df = pd.read_csv(SENTIMENT_FILE)
    # Handle timestamp parsing, works for ISO and mixed:
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["Timestamp"])
    df["Timestamp"] = df["Timestamp"].dt.tz_convert("UTC")
    return df

@st.cache_data
def load_predictions():
    with open(PREDICTION_LOG, "r", encoding="utf-8") as f:
        preds = json.load(f)
    return preds

def get_latest_predictions(preds):
    # Grab latest prediction per coin
    result = {}
    for coin in COINS:
        items = preds.get(coin, [])
        if items:
            result[coin] = items[0]
        else:
            result[coin] = {"timestamp": "", "predicted": None, "actual": None}
    return result

def format_time(ts):
    try:
        dt = parser.isoparse(ts)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return ts

def last24hr_sentiment(df):
    now = pd.Timestamp.utcnow().replace(tzinfo=pd.Timestamp.utcnow().tzinfo)
    cutoff = now - pd.Timedelta(hours=24)
    mask = df["Timestamp"] > cutoff
    d = df[mask]
    res = d.groupby("Coin")["Sentiment"].mean().reindex(COINS)
    return res

# =============== UI ===============
st.set_page_config("Crypto Sentiment Dashboard", layout="wide")
st.title("📊 Crypto Sentiment & Prediction Dashboard")

tabs = st.tabs(["Sentiment Summary (24hr)", "Trends Over Time", "Next Hour Predictions"])

# --- TAB 1: Sentiment Summary (24hr) ---
with tabs[0]:
    st.header("Sentiment Summary (last 24 hours)")
    df = load_sentiment_history()
    sent24 = last24hr_sentiment(df)
    st.dataframe(
        pd.DataFrame({
            "Coin": COINS,
            "24h Avg Sentiment": [f"{v:+.3f}" if pd.notnull(v) else "–" for v in sent24]
        }).set_index("Coin")
    )

# --- TAB 2: Trends Over Time ---
with tabs[1]:
    st.header("Trends Over Time (Zoomed 24-48h)")
    df = load_sentiment_history()
    coin = st.selectbox("Coin", COINS, key="trend_coin")
    now = pd.Timestamp.utcnow().replace(tzinfo=pd.Timestamp.utcnow().tzinfo)
    cutoff = now - pd.Timedelta(hours=48)
    d = df[(df["Coin"] == coin) & (df["Timestamp"] > cutoff)].copy()
    d = d.set_index("Timestamp").sort_index()
    if not d.empty:
        # Resample for clean plot, fill missing
        idx = pd.date_range(d.index.min(), d.index.max(), freq="h", tz="UTC")
        d = d.reindex(idx)
        d["Sentiment"] = d["Sentiment"].interpolate().bfill().ffill()
        d["PriceUSD"] = d["PriceUSD"].interpolate().bfill().ffill()
        import matplotlib.pyplot as plt
        fig, ax1 = plt.subplots(figsize=(10,4))
        ax1.plot(d.index, d["PriceUSD"], label="Price (USD)", linewidth=2)
        ax2 = ax1.twinx()
        ax2.plot(d.index, d["Sentiment"], "r--", label="Sentiment", alpha=0.7)
        ax1.set_ylabel("Price (USD)")
        ax2.set_ylabel("Sentiment")
        fig.legend(loc="upper left")
        ax1.set_title(f"{coin} — Price vs Sentiment (last 48h)")
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.warning("Not enough data for this coin.")

# --- TAB 3: Next Hour Predictions ---
with tabs[2]:
    st.header("Next Hour Predictions (Live ML)")
    preds = load_predictions()
    live = get_latest_predictions(preds)
    hist = load_sentiment_history()
    now = pd.Timestamp.utcnow().replace(tzinfo=pd.Timestamp.utcnow().tzinfo)
    cutoff = now - pd.Timedelta(hours=2)

    result = []
    for coin in COINS:
        pred = live[coin]
        pred_val = pred.get("predicted")
        actual_val = pred.get("actual")
        tstr = format_time(pred.get("timestamp", ""))
        # Try to show most recent price from history
        last_price = (
            hist[(hist["Coin"] == coin) & (hist["Timestamp"] > cutoff)]
            .sort_values("Timestamp")
            .iloc[-1]["PriceUSD"]
            if not hist[(hist["Coin"] == coin) & (hist["Timestamp"] > cutoff)].empty else ""
        )
        diff = (f"{(pred_val-actual_val)/actual_val*100:.2f}%" 
                if actual_val and pred_val else "–")
        acc = (
            "✅" if pred.get("accurate") else
            "❌" if pred.get("accurate") is not None else "–"
        )
        result.append([
            coin, 
            f"${last_price:,.2f}" if last_price else "—",
            f"{pred_val:,.2f}" if pred_val else "—",
            f"{actual_val:,.2f}" if actual_val else "—",
            diff, acc, tstr
        ])
    st.table(
        pd.DataFrame(result, columns=[
            "Coin", "Last Price (USD)", "Predicted Next Price", "Actual", "Diff (%)", "Accurate", "Timestamp"
        ]).set_index("Coin")
    )

    st.info("Predictions update hourly after new data is analyzed. 'Accurate' is checked if prediction error is within ML tolerance (e.g., 4%).")

st.caption("AlphaPulse — Live crypto sentiment & price predictions dashboard.")

