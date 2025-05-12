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

# Logo and header
st.image("alpha_logo.jpg", use_container_width=True)
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("Live crypto sentiment analysis from Reddit and news + historical trends.")

# File paths
csv_path = "sentiment_output.csv"
chart_path = "sentiment_chart.png"
history_file = "sentiment_history.csv"
json_path = "previous_actions.json"

# Utility to load CSVs safely
def load_data(path):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception as e:
            st.error(f"Failed to load {path}: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# Load data & previous alert actions
data = load_data(csv_path)
history = load_data(history_file)
previous_actions = {}
if os.path.exists(json_path):
    with open(json_path, "r") as f:
        previous_actions = json.load(f)

# --- Sidebar: Summary & Alerts ---
st.sidebar.header("📌 Sentiment Summary")

overall = data.groupby("Coin")["Sentiment"].mean()
for coin, avg in overall.items():
    action = "📈 Buy" if avg > 0.2 else "📉 Sell" if avg < -0.2 else "🤝 Hold"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    st.sidebar.write(f"**{coin}**: {avg:.2f} → {action}")
    st.sidebar.caption(f"_Updated: {ts}_")

    key = f"alert_toggle_{coin}"
    if st.sidebar.checkbox(f"🔔 Alert for {coin}", key=key):
        last = previous_actions.get(coin)
        if last != action:
            msg = f"⚠️ **{coin} Action Changed**\nNew Avg Sentiment: {avg:.2f}\n**Suggested Action:** {action}"
            send_telegram_message(msg)
            previous_actions[coin] = action

with open(json_path, "w") as f:
    json.dump(previous_actions, f)

# --- Sentiment Bar Chart ---
if os.path.exists(chart_path):
    st.image(chart_path, caption="Sentiment by Coin and Source", use_container_width=True)

# --- Trends Over Time (Always visible) ---
st.markdown("<h3 style='color: var(--text-color); margin-top:2rem;'>📈 Trends Over Time</h3>", unsafe_allow_html=True)

if not history.empty:
    # KPI Summary Card
    last_update = pd.to_datetime(history["Timestamp"]).max()
    days = history["Timestamp"].str[:10].nunique()
    avg_sent = history["Sentiment"].mean()

    st.markdown(f"""
    <div style='
        padding: 1rem;
        border: 1px solid var(--divider-color);
        border-radius: 10px;
        margin-bottom: 2rem;
        background-color: var(--primary-background-color);
        color: var(--text-color);
    '>
        <div style='margin-bottom:0.5rem;'><b>📅 Last Updated:</b> {last_update}</div>
        <div style='margin-bottom:0.5rem;'><b>📊 Days of History:</b> {days}</div>
        <div><b>📈 Avg Sentiment:</b> {avg_sent:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    # Coin selector & plot
    selected = st.selectbox("Select coin for trend view:", sorted(history["Coin"].unique()))
    subset = history[history["Coin"] == selected]
    if not subset.empty:
        fig, ax1 = plt.subplots(figsize=(10, 5))
        ax1.plot(subset["Timestamp"], subset["Sentiment"], marker="o", color="#1f77b4", label="Sentiment")
        ax1.set_ylabel("Sentiment", color="#1f77b4")
        ax1.tick_params(axis='y', labelcolor="#1f77b4")
        if "PriceUSD" in subset.columns:
            ax2 = ax1.twinx()
            ax2.plot(subset["Timestamp"], subset["PriceUSD"], linestyle="--", color="#2ca02c", label="Price")
            ax2.set_ylabel("Price (USD)", color="#2ca02c")
            ax2.tick_params(axis='y', labelcolor="#2ca02c")
        ax1.set_xlabel("Time")
        plt.title(f"{selected} - Sentiment and Price Over Time")
        fig.autofmt_xdate()
        st.pyplot(fig)
    else:
        st.info("No historical data yet for this coin.")
else:
    st.warning("📉 No historical trend data available.")

# --- Sentiment Details Table ---
st.subheader("📋 Sentiment Details")
filter_coin = st.selectbox("Filter by coin:", ["All"] + sorted(data["Coin"].unique()))
filtered = data if filter_coin == "All" else data[data["Coin"] == filter_coin]
cols = ["Source", "Sentiment", "SuggestedAction", "Text", "Link"]
display = [c for c in cols if c in filtered.columns]
if not filtered.empty and display:
    st.dataframe(filtered[display].sort_values(by="Sentiment", ascending=False), use_container_width=True)
else:
    st.info("No sentiment data to display.")
