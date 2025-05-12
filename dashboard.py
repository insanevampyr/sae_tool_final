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

# Logo & Header
if os.path.exists("alpha_logo.jpg"):
    st.image("alpha_logo.jpg", use_container_width=True)
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("Live crypto sentiment analysis from Reddit and news + historical trends.")

# File paths
csv_path       = "sentiment_output.csv"
chart_path     = "sentiment_chart.png"
history_path   = "sentiment_history.csv"
actions_path   = "previous_actions.json"

def load_df(path):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception as e:
            st.error(f"Failed to load {path}: {e}")
    return pd.DataFrame()

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

# Load data
data         = load_df(csv_path)
history      = load_df(history_path)
prev_actions = load_json(actions_path)
prices       = fetch_prices()

# --- Sidebar: Summary & Alerts ---
st.sidebar.header("📌 Sentiment Summary")

if not data.empty:
    overall = data.groupby("Coin")["Sentiment"].mean()
    for coin, sent in overall.items():
        action    = "📈 Buy" if sent>0.2 else "📉 Sell" if sent< -0.2 else "🤝 Hold"
        updated   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        st.sidebar.write(f"**{coin}**: {sent:.2f} → {action}")
        st.sidebar.caption(f"_Updated: {updated}_")

        chk = st.sidebar.checkbox(f"🔔 Alert for {coin}", key=f"alert_{coin}")
        if chk and prev_actions.get(coin) != action:
            msg = f"⚠️ **{coin} Action Changed**\nAvg Sentiment: {sent:.2f}\nSuggested: {action}"
            send_telegram_message(msg)
            prev_actions[coin] = action

    save_json(actions_path, prev_actions)
else:
    st.sidebar.info("No sentiment data yet.")

# --- Bar Chart ---
if os.path.exists(chart_path):
    st.image(chart_path, caption="Sentiment by Coin and Source", use_container_width=True)

# --- Trends Over Time (Always visible) ---
st.markdown(
    "<h3 style='color:#ffffff; background-color:#000000; padding:5px;'>📈 Trends Over Time</h3>",
    unsafe_allow_html=True
)

if not history.empty:
    # summary card
    last_upd     = pd.to_datetime(history["Timestamp"], errors="coerce").max()
    days_of_data = history["Timestamp"].str[:10].nunique()
    avg_all      = history["Sentiment"].mean()
    st.markdown(f"""
    <div style="background:#f0f2f6; padding:10px; border-radius:8px; margin-bottom:1rem;">
      📅 <b>Last Updated:</b> {last_upd}<br>
      📊 <b>Days of History:</b> {days_of_data}<br>
      📈 <b>Avg Sentiment:</b> {avg_all:.2f}
    </div>""", unsafe_allow_html=True)

    coin_sel    = st.selectbox("Select coin:", ["All"] + history["Coin"].unique().tolist())
    subset      = history if coin_sel=="All" else history[history["Coin"]==coin_sel]

    if not subset.empty:
        fig, ax1 = plt.subplots(figsize=(10,5))
        ax1.plot(subset["Timestamp"], subset["Sentiment"], 'o-', color="#1f77b4", label="Sentiment")
        ax1.set_ylabel("Sentiment", color="#1f77b4")
        ax1.tick_params(axis='y', labelcolor="#1f77b4")

        if "PriceUSD" in subset.columns:
            ax2 = ax1.twinx()
            ax2.plot(subset["Timestamp"], subset["PriceUSD"], '--', color="#2ca02c", label="Price")
            ax2.set_ylabel("Price USD", color="#2ca02c")
            ax2.tick_params(axis='y', labelcolor="#2ca02c")

        plt.title(f"{coin_sel} Trends")
        fig.autofmt_xdate()
        st.pyplot(fig)
    else:
        st.info("No history for this selection.")
else:
    st.info("No historical data available.")

# --- Sentiment Details Table ---
st.subheader("📋 Sentiment Details")
if not data.empty:
    df = data.drop_duplicates(subset=["Source","Coin","Text"])
    coin_filter = st.selectbox("Filter by coin:", ["All"] + df["Coin"].unique().tolist())
    view        = df if coin_filter=="All" else df[df["Coin"]==coin_filter]
    st.dataframe(view[["Source","Coin","Sentiment","SuggestedAction","Text","Link"]],
                 use_container_width=True)
else:
    st.info("No data to display.")
