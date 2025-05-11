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
st.markdown("Track live sentiment and price trends for top cryptocurrencies.")

# Load data
csv_file = "sentiment_output.csv"
history_file = "sentiment_history.csv"
json_path = "previous_actions.json"

# Sidebar toggle
st.sidebar.title("⚙️ Settings")
alert_toggle = st.sidebar.checkbox("🔔 Enable Telegram Alerts", value=True)

# Load current data
if os.path.exists(csv_file):
    df = pd.read_csv(csv_file)
else:
    st.error("sentiment_output.csv not found. Run analyze.py first.")
    st.stop()

# Load historical data
if os.path.exists(history_file):
    history = pd.read_csv(history_file)
else:
    history = pd.DataFrame()

# Load previous action state
if os.path.exists(json_path):
    with open(json_path, "r") as f:
        previous_actions = json.load(f)
else:
    previous_actions = {}

# ─────────────────────────────────────────────────────────────
# 📈 TRENDS OVER TIME SECTION
# ─────────────────────────────────────────────────────────────
st.header("📈 Trends Over Time")
if not history.empty:
    coin_options = sorted(history["Coin"].unique())
    selected_coin = st.selectbox("Choose a coin:", coin_options)
    coin_history = history[history["Coin"] == selected_coin]

    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(pd.to_datetime(coin_history["Timestamp"]), coin_history["Sentiment"], label="Sentiment", color="blue")
    ax1.set_ylabel("Sentiment", color="blue")
    ax1.tick_params(axis='y', labelcolor='blue')

    if "PriceUSD" in coin_history.columns:
        ax2 = ax1.twinx()
        ax2.plot(pd.to_datetime(coin_history["Timestamp"]), coin_history["PriceUSD"], color="green", linestyle="--", label="Price (USD)")
        ax2.set_ylabel("Price (USD)", color="green")
        ax2.tick_params(axis='y', labelcolor='green')

    fig.autofmt_xdate()
    st.pyplot(fig)
else:
    st.info("No historical sentiment data found.")

# ─────────────────────────────────────────────────────────────
# 📌 CURRENT SENTIMENT SUMMARY
# ─────────────────────────────────────────────────────────────
st.header("📌 Current Sentiment Summary")
st.image("sentiment_chart.png", caption="Sentiment by Coin and Source", use_container_width=True)

summary = df.groupby(["Coin", "Source"])["Sentiment"].mean().reset_index()
summary["SuggestedAction"] = summary["Sentiment"].apply(
    lambda s: "📈 Buy" if s > 0.2 else "📉 Sell" if s < -0.2 else "🤝 Hold"
)

st.dataframe(summary.sort_values(by="Sentiment", ascending=False), use_container_width=True)

# ─────────────────────────────────────────────────────────────
# 🔔 TELEGRAM ALERTS (ONLY IF ENABLED)
# ─────────────────────────────────────────────────────────────
if alert_toggle:
    for coin in df["Coin"].unique():
        avg_sent = df[df["Coin"] == coin]["Sentiment"].mean()
        action = "📈 Buy" if avg_sent > 0.2 else "📉 Sell" if avg_sent < -0.2 else "🤝 Hold"
        last = previous_actions.get(coin)
        if last != action:
            msg = f"⚠️ {coin} action changed\nSentiment: {avg_sent:.2f}\nAction: {action}"
            send_telegram_message(msg)
            previous_actions[coin] = action

    with open(json_path, "w") as f:
        json.dump(previous_actions, f)

# ─────────────────────────────────────────────────────────────
# 🔎 BREAKDOWN TABLE
# ─────────────────────────────────────────────────────────────
st.header("🔍 Breakdown by Posts")
coin_filter = st.selectbox("Filter by coin:", ["All"] + sorted(df["Coin"].unique()))
filtered = df if coin_filter == "All" else df[df["Coin"] == coin_filter]

expected_cols = ["Source", "Sentiment", "SuggestedAction", "Text", "Link"]
available_cols = [col for col in expected_cols if col in filtered.columns]

if available_cols:
    st.dataframe(filtered[available_cols].sort_values(by="Sentiment", ascending=False), use_container_width=True)
else:
    st.warning("No valid columns to display.")
