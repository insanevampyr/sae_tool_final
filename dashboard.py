import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import json
from datetime import datetime, timezone
from send_telegram import send_telegram_message
from reddit_fetch import fetch_reddit_posts
from rss_fetch import fetch_rss_articles
from analyze_sentiment import analyze_sentiment

st.set_page_config(page_title="Crypto Sentiment Dashboard", layout="wide")

st.title("📊 Crypto Sentiment Dashboard")
st.markdown("Live crypto sentiment analysis from Reddit and crypto news + historical trends.")

csv_file = "sentiment_output.csv"
history_file = "sentiment_history.csv"
chart_file = "sentiment_chart.png"
previous_actions_file = "previous_actions.json"

coins = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]

# Load sentiment data
if not os.path.exists(csv_file):
    st.error("No sentiment data found. Please run analyze.py first.")
    st.stop()

data = pd.read_csv(csv_file)

# ---------------- Sidebar Setup ---------------- #
st.sidebar.header("📌 Alerts & Summary")
if os.path.exists(previous_actions_file):
    with open(previous_actions_file, "r") as f:
        previous_actions = json.load(f)
else:
    previous_actions = {}

for coin in coins:
    coin_df = data[data["Coin"] == coin]
    avg_sentiment = coin_df["Sentiment"].mean()
    action = "📈 Buy" if avg_sentiment > 0.2 else "📉 Sell" if avg_sentiment < -0.2 else "🤝 Hold"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    alert_toggle = st.sidebar.checkbox(f"🔔 Alert for {coin}", key=f"alert_toggle_{coin}")

    if alert_toggle:
        last = previous_actions.get(coin)
        if last != action:
            msg = f"⚠️ {coin} Action Changed\nNew Sentiment: {avg_sentiment:.2f}\n**Action:** {action}"
            send_telegram_message(msg)
            previous_actions[coin] = action

    st.sidebar.write(f"**{coin}** → `{avg_sentiment:.2f}` → **{action}**")
    st.sidebar.caption(f"_Updated: {timestamp}_")

with open(previous_actions_file, "w") as f:
    json.dump(previous_actions, f)

# ---------------- Trends Over Time ---------------- #
st.subheader("📈 Trends Over Time")
if os.path.exists(history_file):
    history = pd.read_csv(history_file)
    for coin in coins:
        coin_history = history[history["Coin"] == coin]
        if coin_history.empty:
            continue
        coin_history["Timestamp"] = pd.to_datetime(coin_history["Timestamp"])

        fig, ax1 = plt.subplots(figsize=(8, 4))
        ax1.plot(coin_history["Timestamp"], coin_history["Sentiment"], label="Sentiment", color="blue")
        ax1.set_ylabel("Sentiment", color="blue")
        ax1.tick_params(axis='y', labelcolor="blue")

        if "PriceUSD" in coin_history.columns:
            ax2 = ax1.twinx()
            ax2.plot(coin_history["Timestamp"], coin_history["PriceUSD"], color="green", linestyle="--", label="Price")
            ax2.set_ylabel("Price (USD)", color="green")
            ax2.tick_params(axis='y', labelcolor="green")

        plt.title(f"{coin} - Sentiment & Price Over Time")
        st.pyplot(fig)
else:
    st.warning("No sentiment history found. Run `analyze.py` at least once.")

# ---------------- Sentiment Chart ---------------- #
st.subheader("📊 Current Sentiment Breakdown")
if os.path.exists(chart_file):
    st.image(chart_file, caption="Sentiment by Coin and Source", use_column_width=True)

# ---------------- Data Table ---------------- #
st.subheader("📋 Raw Sentiment Data")
coin_filter = st.selectbox("Filter by coin:", ["All"] + coins)
filtered = data if coin_filter == "All" else data[data["Coin"] == coin_filter]

cols_to_show = ["Source", "Sentiment", "SuggestedAction", "Text", "Link"]
available = [col for col in cols_to_show if col in filtered.columns]

if available:
    st.dataframe(filtered[available].sort_values(by="Sentiment", ascending=False))
else:
    st.warning("No matching columns found.")
