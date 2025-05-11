import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timezone
import os
from analyze_sentiment import analyze_sentiment
from reddit_fetch import fetch_reddit_posts
from rss_fetch import fetch_rss_articles
from send_telegram import send_telegram_message

st.set_page_config(page_title="Crypto Sentiment Dashboard", layout="wide")
st.title("📊 Crypto Sentiment Dashboard")
st.markdown("Live sentiment and trend analysis for top cryptocurrencies.")

# --- Paths ---
csv_path = "sentiment_output.csv"
chart_path = "sentiment_chart.png"
history_path = "sentiment_history.csv"

# --- Load latest sentiment CSV ---
if not os.path.exists(csv_path):
    st.error("sentiment_output.csv not found. Please run analyze.py first.")
    st.stop()

latest_data = pd.read_csv(csv_path)

# --- Load historical sentiment CSV ---
if os.path.exists(history_path):
    history = pd.read_csv(history_path)
else:
    history = pd.DataFrame()

# --- Sidebar Summary ---
st.sidebar.header("📌 Sentiment Summary")
summary = latest_data.groupby("Coin")["Sentiment"].mean()
for coin, score in summary.items():
    action = "📈 Buy" if score > 0.2 else "📉 Sell" if score < -0.2 else "🤝 Hold"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    st.sidebar.markdown(f"**{coin}**\n→ Sentiment: `{score:.2f}`\n→ Suggestion: `{action}`\n→ _{timestamp}_")

# --- Trends Over Time ---
st.subheader("📈 Trends Over Time")
coin_list = latest_data["Coin"].unique().tolist()
selected = st.selectbox("Choose a coin to view trend: ", coin_list)

if selected and not history.empty:
    coin_data = history[history["Coin"] == selected].copy()
    coin_data["Timestamp"] = pd.to_datetime(coin_data["Timestamp"])

    fig, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(coin_data["Timestamp"], coin_data["Sentiment"], label="Sentiment", color="blue")
    ax1.set_ylabel("Sentiment")

    if "PriceUSD" in coin_data.columns:
        ax2 = ax1.twinx()
        ax2.plot(coin_data["Timestamp"], coin_data["PriceUSD"], color="green", linestyle="--", label="Price (USD)")
        ax2.set_ylabel("Price (USD)")

    ax1.set_title(f"Sentiment & Price Over Time: {selected}")
    fig.autofmt_xdate()
    fig.tight_layout()
    st.pyplot(fig)
else:
    st.warning("No historical data available.")

# --- Sentiment Breakdown Table ---
st.subheader("📊 Latest Sentiment Breakdown")
columns = ["Coin", "Source", "Sentiment", "SuggestedAction", "Text", "Link"]
if all(col in latest_data.columns for col in columns):
    st.dataframe(latest_data[columns].sort_values(by="Sentiment", ascending=False), use_container_width=True)
else:
    st.warning("Some expected columns are missing in sentiment_output.csv")
