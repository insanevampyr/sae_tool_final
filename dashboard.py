# dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime, timezone
from send_telegram import send_telegram_message
from reddit_fetch import fetch_reddit_posts
from rss_fetch import fetch_rss_articles
from analyze_sentiment import analyze_sentiment
from fetch_prices import fetch_prices

st.set_page_config(page_title="AlphaPulse | Sentiment Dashboard", layout="wide")

st.image("alpha_logo.jpg", use_column_width=True)
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("Live crypto sentiment analysis from Reddit and news + historical trends.")

csv_path = "sentiment_output.csv"
chart_path = "sentiment_chart.png"
history_file = "sentiment_history.csv"
json_path = "previous_actions.json"

def load_data(path):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception as e:
            st.error(f"Failed to load {path}: {e}")
            return pd.DataFrame()
    else:
        return pd.DataFrame()

def load_previous_actions():
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            return json.load(f)
    return {}

def save_previous_actions(data):
    with open(json_path, "w") as f:
        json.dump(data, f)

# Load data
data = load_data(csv_path)
history = load_data(history_file)
previous_actions = load_previous_actions()
prices = fetch_prices()

# --- Sidebar Summary & Alerts ---
st.sidebar.header("📌 Sentiment Summary")

overall_sentiments = data.groupby("Coin")["Sentiment"].mean()
for coin, sentiment in overall_sentiments.items():
    action = "📈 Buy" if sentiment > 0.2 else "📉 Sell" if sentiment < -0.2 else "🤝 Hold"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    st.sidebar.write(f"**{coin}**: {sentiment:.2f} → {action}")
    st.sidebar.caption(f"_Updated: {timestamp}_")

    toggle_key = f"alert_toggle_{coin}"
    if st.sidebar.checkbox(f"🔔 Alert for {coin}", key=toggle_key):
        last_action = previous_actions.get(coin)
        if last_action != action:
            msg = f"⚠️ **{coin} Action Changed**\nNew Avg Sentiment: {sentiment:.2f}\n**Suggested Action:** {action}"
            send_telegram_message(msg)
            previous_actions[coin] = action

save_previous_actions(previous_actions)

# --- Sentiment Bar Chart ---
if os.path.exists(chart_path):
    st.image(chart_path, caption="Sentiment by Coin and Source", use_container_width=True)

# --- Trends Over Time (Always visible)
st.markdown("<h3 style='color: var(--text-color);'>📈 Trends Over Time</h3>", unsafe_allow_html=True)

if not history.empty:
    # Quick Summary Card
    last_update = pd.to_datetime(history["Timestamp"]).max()
    total_days = history["Timestamp"].str[:10].nunique()
    avg_sentiment_all = history["Sentiment"].mean()

    st.markdown(f"""
    <div style='padding: 1rem; border: 1px solid #444; border-radius: 10px; margin-bottom: 1rem; background-color: rgba(255,255,255,0.05);'>
        <b>📅 Last Updated:</b> {last_update}<br>
        <b>📊 Days of Data:</b> {total_days}<br>
        <b>📈 Avg Sentiment (All):</b> {avg_sentiment_all:.2f}
    </div>
    """, unsafe_allow_html=True)

    selected_coin = st.selectbox("Select coin for trend view:", sorted(history["Coin"].unique()))
    coin_history = history[history["Coin"] == selected_coin]

    if not coin_history.empty:
        fig, ax1 = plt.subplots(figsize=(10, 5))
        ax1.plot(coin_history["Timestamp"], coin_history["Sentiment"], marker="o", color="#1f77b4", label="Sentiment")
        ax1.set_ylabel("Sentiment", color="#1f77b4")
        ax1.tick_params(axis='y', labelcolor="#1f77b4")

        if "PriceUSD" in coin_history.columns:
            ax2 = ax1.twinx()
            ax2.plot(coin_history["Timestamp"], coin_history["PriceUSD"], linestyle="--", color="#2ca02c", label="Price")
            ax2.set_ylabel("Price (USD)", color="#2ca02c")
            ax2.tick_params(axis='y', labelcolor="#2ca02c")

        ax1.set_xlabel("Time")
        fig.autofmt_xdate()
        plt.title(f"{selected_coin} - Sentiment and Price Over Time")
        st.pyplot(fig)
    else:
        st.info("No historical data yet for this coin.")
else:
    st.warning("📉 No historical trend data available.")

# --- Sentiment Details Table ---
st.subheader("📋 Sentiment Details")
coin_filter = st.selectbox("Filter by coin:", ["All"] + sorted(data["Coin"].unique()))
filtered = data if coin_filter == "All" else data[data["Coin"] == coin_filter]
cols = ["Source", "Sentiment", "SuggestedAction", "Text", "Link"]
display_cols = [col for col in cols if col in filtered.columns]

if not filtered.empty and display_cols:
    st.dataframe(filtered[display_cols].sort_values(by="Sentiment", ascending=False))
else:
    st.info("No sentiment data to display.")
