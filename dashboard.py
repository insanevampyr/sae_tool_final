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

# --- HEADER & BRANDING ---
st.image("alpha_logo.jpg", use_container_width=True)
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("Live crypto sentiment analysis from Reddit and news + historical trends.")

# --- FILE PATHS ---
csv_path       = "sentiment_output.csv"
chart_path     = "sentiment_chart.png"
history_file   = "sentiment_history.csv"
json_path      = "previous_actions.json"

# --- DATA LOADER WITH MALFORMED-LINE SKIP ---
def load_data(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(
            path,
            engine="python",
            on_bad_lines="skip",       # skip malformed rows
            quotechar='"',
            skip_blank_lines=True
        )
    except Exception as e:
        st.error(f"Failed to load {path}: {e}")
        return pd.DataFrame()

def load_previous_actions():
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            return json.load(f)
    return {}

def save_previous_actions(data):
    with open(json_path, "w") as f:
        json.dump(data, f)

# --- LOAD & CLEAN DATA ---
data             = load_data(csv_path)
history          = load_data(history_file)
previous_actions = load_previous_actions()
prices           = fetch_prices()

# ensure numeric
if "Sentiment" in data.columns:
    data["Sentiment"] = pd.to_numeric(data["Sentiment"], errors="coerce")
if "Sentiment" in history.columns:
    history["Sentiment"] = pd.to_numeric(history["Sentiment"], errors="coerce")
if "PriceUSD" in history.columns:
    history["PriceUSD"] = pd.to_numeric(history["PriceUSD"], errors="coerce")

# --- SIDEBAR: SUMMARY & ALERTS ---
st.sidebar.header("📌 Sentiment Summary")

if not data.empty and {"Coin","Sentiment"}.issubset(data.columns):
    overall = data.groupby("Coin")["Sentiment"].mean()
    for coin, sentiment in overall.items():
        action    = "📈 Buy" if sentiment > 0.2 else "📉 Sell" if sentiment < -0.2 else "🤝 Hold"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        st.sidebar.write(f"**{coin}**: {sentiment:.2f} → {action}")
        st.sidebar.caption(f"_Updated: {timestamp}_")

        toggle_key = f"alert_toggle_{coin}"
        if st.sidebar.checkbox(f"🔔 Alert for {coin}", key=toggle_key):
            last = previous_actions.get(coin)
            if last != action:
                msg = f"⚠️ **{coin} Action Changed**\nNew Avg Sentiment: {sentiment:.2f}\n**Suggested Action:** {action}"
                send_telegram_message(msg)
                previous_actions[coin] = action
else:
    st.sidebar.warning("No sentiment data to summarize.")

save_previous_actions(previous_actions)

# --- BAR CHART ---
if os.path.exists(chart_path):
    st.image(chart_path, caption="Sentiment by Coin and Source", use_container_width=True)

# --- TRENDS OVER TIME ---
st.markdown("<h2 style='color:#FF8C00;'>📈 Trends Over Time</h2>", unsafe_allow_html=True)

if not history.empty and {"Timestamp","Coin","Sentiment"}.issubset(history.columns):
    last_update  = pd.to_datetime(history["Timestamp"], errors="coerce").max()
    total_days   = history["Timestamp"].str[:10].nunique()
    avg_sent_all = history["Sentiment"].mean()
    st.markdown(f"""
    <div style='margin:1rem 0;padding:1rem;border:1px solid #444;border-radius:8px;
                background-color:rgba(255,255,255,0.1);'>
      <strong>📅 Last Updated:</strong> {last_update}<br>
      <strong>📊 Days of History:</strong> {total_days}<br>
      <strong>📈 Avg Sentiment (All):</strong> {avg_sent_all:.2f}
    </div>
    """, unsafe_allow_html=True)

    coin_sel  = st.selectbox("Select coin for trend view:", sorted(history["Coin"].unique()))
    coin_hist = history[history["Coin"] == coin_sel]

    if not coin_hist.empty:
        fig, ax1 = plt.subplots(figsize=(10,4))
        ax1.plot(coin_hist["Timestamp"], coin_hist["Sentiment"],
                 marker="o", color="#1f77b4", label="Sentiment")
        ax1.set_ylabel("Sentiment", color="#1f77b4")
        ax1.tick_params(axis='y', labelcolor="#1f77b4")

        if "PriceUSD" in coin_hist.columns:
            ax2 = ax1.twinx()
            ax2.plot(coin_hist["Timestamp"], coin_hist["PriceUSD"],
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

# --- DETAILS TABLE ---
st.subheader("📋 Sentiment Details")
coins = ["All"] + sorted(data["Coin"].unique()) if "Coin" in data.columns else ["All"]
sel   = st.selectbox("Filter by coin:", coins)
filtered = data if sel=="All" else data[data["Coin"]==sel]
cols     = ["Source","Sentiment","SuggestedAction","Text","Link"]
show     = [c for c in cols if c in filtered.columns]
if not filtered.empty and show:
    st.dataframe(filtered[show].sort_values("Sentiment",ascending=False),
                 use_container_width=True)
else:
    st.info("No sentiment data to display.")
