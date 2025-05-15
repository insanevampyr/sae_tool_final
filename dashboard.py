# dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import json
import os
from datetime import datetime, timezone, timedelta
from sklearn.linear_model import LinearRegression
import numpy as np

from send_telegram import send_telegram_message
from fetch_prices import fetch_prices

# File paths
csv_path = "sentiment_output.csv"
history_file = "sentiment_history.csv"
prediction_log = "prediction_log.json"
last_action_path = "last_sent_action.json"

# Init
st.set_page_config(page_title="AlphaPulse Dashboard", layout="wide")
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")

def load_csv(path):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def predict_price(df):
    df = df.dropna(subset=["PriceUSD", "Sentiment"])
    if len(df) < 6:
        return None
    df = df.sort_values("Timestamp")
    X = df["Sentiment"].values[-6:].reshape(-1, 1)
    y = df["PriceUSD"].values[-6:]
    model = LinearRegression().fit(X, y)
    prediction = model.predict([[df["Sentiment"].values[-1]]])[0]
    return prediction

def send_price_alert(coin, predicted_price, current_price, threshold_pct=4.0):
    last_actions = load_json(last_action_path)
    key = f"{coin}"
    diff_pct = ((predicted_price - current_price) / current_price) * 100

    if key not in last_actions or abs(diff_pct) >= threshold_pct:
        msg = f"📉 ML Prediction for {coin}:\nExpected Price: ${predicted_price:,.2f}\nCurrent: ${current_price:,.2f}\nDiff: {diff_pct:.2f}%"
        send_telegram_message(msg)
        last_actions[key] = predicted_price
        save_json(last_action_path, last_actions)

# Load data
data = load_csv(csv_path)
history = load_csv(history_file)
prices = fetch_prices()

# Parse timestamps
for df in [data, history]:
    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")

# Sidebar - Sentiment Summary
st.sidebar.header("📌 Sentiment Summary")
cutoff = datetime.now(timezone.utc) - timedelta(days=1)
recent = data[data["Timestamp"] >= cutoff]

if recent.empty:
    st.sidebar.warning("No data in last 24h.")
else:
    overall = recent.groupby("Coin")["Sentiment"].mean()
    for coin, avg in overall.items():
        action = "📈 Buy" if avg > 0.2 else "📉 Sell" if avg < -0.2 else "🤝 Hold"
        st.sidebar.write(f"**{coin}**: {avg:.2f} → {action}")

# ML Predictions + Accuracy
st.markdown("### 🤖 ML Price Predictions (Next Hour)")
pred_df = pd.DataFrame()
if not history.empty:
    pred_log = load_json(prediction_log)
    acc_results = []
    for coin in sorted(history["Coin"].dropna().unique()):
        df = history[(history["Coin"] == coin)].copy()
        pred_price = predict_price(df)
        cur_price = prices.get(coin, None)

        if pred_price and cur_price:
            # Log prediction
            timestamp = datetime.now(timezone.utc).isoformat()
            entry = {
                "timestamp": timestamp,
                "coin": coin,
                "predicted_price": round(pred_price, 2),
                "actual_price": round(cur_price, 2)
            }
            pred_log.append(entry)
            save_json(prediction_log, pred_log)

            # Send alert if needed
            send_price_alert(coin, pred_price, cur_price)

            # Accuracy (last 24h)
            last_24h = [
                p for p in pred_log if p["coin"] == coin and
                datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00")) > datetime.now(timezone.utc) - timedelta(hours=24)
            ]
            correct = sum(1 for p in last_24h if abs((p["actual_price"] - p["predicted_price"]) / p["actual_price"]) <= 0.04)
            acc = f"{(100 * correct / len(last_24h)):.1f}%" if last_24h else "N/A"

            st.success(f"{coin}: Predicted ${pred_price:,.2f} | Current ${cur_price:,.2f} | 24h Accuracy: {acc}")
        else:
            st.info(f"{coin}: Not enough data to predict.")

# Trend chart
st.markdown("### 📈 Trends Over Time")
if not history.empty:
    coin = st.selectbox("View coin trend", sorted(history["Coin"].unique()))
    df_c = history[history["Coin"] == coin].copy()
    df_c = df_c.dropna(subset=["Timestamp", "Sentiment"])
    if not df_c.empty:
        fig, ax = plt.subplots()
        ax.plot(df_c["Timestamp"], df_c["Sentiment"], marker="o", label="Sentiment")
        if "PriceUSD" in df_c:
            ax2 = ax.twinx()
            ax2.plot(df_c["Timestamp"], df_c["PriceUSD"], color="green", linestyle="--", label="PriceUSD")
        st.pyplot(fig)
    else:
        st.info("No data for this coin.")

# Sentiment Details Table
st.markdown("### 📋 Sentiment Details")
if not data.empty:
    view = data.drop_duplicates(subset=["Coin", "Source", "Text"])
    col_order = ["Coin", "Sentiment", "Action", "Text", "Source", "Link", "Timestamp"]
    for col in col_order:
        if col not in view.columns:
            view[col] = ""
    st.dataframe(view[col_order].sort_values("Timestamp", ascending=False), use_container_width=True)
else:
    st.info("No sentiment data available.")
