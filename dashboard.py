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

# ─── HEADER & LOGO ─────────────────────────────────────────────────────────────
st.image("alpha_logo.jpg", use_container_width=True)
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("Live crypto sentiment analysis from Reddit and news + historical trends.")

# ─── PATHS ─────────────────────────────────────────────────────────────────────
csv_path     = "sentiment_output.csv"
chart_path   = "sentiment_chart.png"
history_path = "sentiment_history.csv"
json_path    = "previous_actions.json"

# ─── HELPERS ───────────────────────────────────────────────────────────────────
def load_data(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path, engine="python", on_bad_lines="skip")
    except Exception as e:
        st.error(f"Failed to load {path}: {e}")
        return pd.DataFrame()

def load_json(path):
    if os.path.exists(path):
        with open(path,"r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path,"w") as f:
        json.dump(data, f)

# ─── LOAD & CLEAN ────────────────────────────────────────────────────────────────
data             = load_data(csv_path)
history          = load_data(history_path)
previous_actions = load_json(json_path)
prices           = fetch_prices()

# coerce numeric & drop bad
for col in ("Sentiment","PriceUSD"):
    if col in history.columns:
        history[col] = pd.to_numeric(history[col], errors="coerce")
history = history.dropna(subset=["Coin"])  # get rid of float-NaNs in coin column

# ─── SIDEBAR: SUMMARY & ALERTS ─────────────────────────────────────────────────
st.sidebar.header("📌 Sentiment Summary")

if {"Coin","Sentiment"}.issubset(data.columns) and not data.empty:
    overall = data.groupby("Coin")["Sentiment"].mean()
    for coin, sentiment in overall.items():
        action    = "📈 Buy" if sentiment > 0.2 else "📉 Sell" if sentiment < -0.2 else "🤝 Hold"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        st.sidebar.write(f"**{coin}**: {sentiment:.2f} → {action}")
        st.sidebar.caption(f"_Updated: {timestamp}_")

        key = f"alert_{coin}"
        if st.sidebar.checkbox(f"🔔 Alert for {coin}", key=key):
            last = previous_actions.get(coin)
            if last != action:
                msg = f"⚠️ **{coin} Action Changed**\nAvg Sentiment: {sentiment:.2f}\nAction: {action}"
                send_telegram_message(msg)
                previous_actions[coin] = action
else:
    st.sidebar.warning("No sentiment data to summarize.")

save_json(json_path, previous_actions)

# ─── BAR CHART ─────────────────────────────────────────────────────────────────
if os.path.exists(chart_path):
    st.image(chart_path, caption="Sentiment by Coin and Source", use_container_width=True)

# ─── TRENDS OVER TIME ───────────────────────────────────────────────────────────
st.markdown("<h2 style='color: var(--primary-color) !important;'>📈 Trends Over Time</h2>", unsafe_allow_html=True)

if not history.empty and {"Timestamp","Coin","Sentiment"}.issubset(history.columns):
    # parse timestamps
    history["Timestamp"] = pd.to_datetime(history["Timestamp"], errors="coerce")
    valid_times = history["Timestamp"].dropna()
    last_update = valid_times.max() if not valid_times.empty else None
    days = valid_times.dt.date.nunique()

    avg_all = history["Sentiment"].mean()
    if pd.isna(avg_all):
        avg_all = 0.0

    # summary card
    st.markdown(f"""
    <div style='padding:1rem;border:1px solid #444;border-radius:8px;
                background-color:rgba(255,255,255,0.1);margin-bottom:1rem;'>
      <strong>📅 Last Updated:</strong> {last_update or "No data yet"}<br>
      <strong>📊 Days of History:</strong> {days}<br>
      <strong>📈 Avg Sentiment (All):</strong> {avg_all:.2f}
    </div>
    """, unsafe_allow_html=True)

    coins = sorted(history["Coin"].astype(str).unique())
    coin_sel = st.selectbox("Select coin for trend view:", coins)
    ch = history[history["Coin"]==coin_sel]

    if not ch.empty:
        fig, ax1 = plt.subplots(figsize=(10,4))
        ax1.plot(ch["Timestamp"], ch["Sentiment"],
                 marker="o", color="#1f77b4", label="Sentiment")
        ax1.set_ylabel("Sentiment", color="#1f77b4")
        ax1.tick_params(axis='y', labelcolor="#1f77b4")

        if "PriceUSD" in ch.columns:
            ax2 = ax1.twinx()
            ax2.plot(ch["Timestamp"], ch["PriceUSD"],
                     linestyle="--", color="#2ca02c", label="Price")
            ax2.set_ylabel("Price (USD)", color="#2ca02c")
            ax2.tick_params(axis='y', labelcolor="#2ca02c")

        ax1.set_xlabel("Time")
        fig.autofmt_xdate()
        plt.title(f"{coin_sel} – Sentiment & Price Over Time")
        st.pyplot(fig)
    else:
        st.info("No historical data yet for this coin.")
else:
    st.warning("📉 No historical trend data available.")

# ─── DETAILS TABLE ──────────────────────────────────────────────────────────────
st.subheader("📋 Sentiment Details")
if {"Coin","Sentiment"}.issubset(data.columns):
    coins = ["All"] + sorted(data["Coin"].astype(str).unique())
else:
    coins = ["All"]
sel = st.selectbox("Filter by coin:", coins)
filtered = data if sel=="All" else data[data["Coin"]==sel]

cols = ["Source","Sentiment","SuggestedAction","Text","Link"]
show = [c for c in cols if c in filtered.columns]
if not filtered.empty and show:
    st.dataframe(filtered[show].sort_values("Sentiment",ascending=False), use_container_width=True)
else:
    st.info("No sentiment data to display.")
