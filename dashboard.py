# dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime, timezone
from send_telegram import send_telegram_message
from reddit_fetch    import fetch_reddit_posts
from rss_fetch       import fetch_rss_articles
from analyze_sentiment import analyze_sentiment
from fetch_prices    import fetch_prices

st.set_page_config(page_title="AlphaPulse | Sentiment Dashboard", layout="wide")

# — Branding —
st.image("alpha_logo.jpg", use_container_width=True)
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("Live crypto sentiment analysis from Reddit and news + historical trends.")

# — File paths —
csv_path      = "sentiment_output.csv"
chart_path    = "sentiment_chart.png"
history_file  = "sentiment_history.csv"
json_path     = "previous_actions.json"

def load_data(path):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception as e:
            st.error(f"Failed to load {path}: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def load_previous_actions():
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            return json.load(f)
    return {}

def save_previous_actions(data):
    with open(json_path, "w") as f:
        json.dump(data, f)

# — Load & de-dup sentiment data —
data = load_data(csv_path)
if not data.empty:
    # drop exact duplicates across these key columns
    data = data.drop_duplicates(subset=["Source","Coin","Text","Link","Timestamp"], keep="first")
history           = load_data(history_file)
previous_actions  = load_previous_actions()
prices            = fetch_prices()

# — Sidebar: summary & alerts —
st.sidebar.header("📌 Sentiment Summary")
overall = data.groupby("Coin")["Sentiment"].mean()
for coin, sentiment in overall.items():
    action    = "📈 Buy" if sentiment>0.2 else "📉 Sell" if sentiment<-0.2 else "🤝 Hold"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    st.sidebar.write(f"**{coin}**: {sentiment:.2f} → {action}")
    st.sidebar.caption(f"_Updated: {timestamp}_")

    key = f"alert_toggle_{coin}"
    if st.sidebar.checkbox(f"🔔 Alert for {coin}", key=key):
        last = previous_actions.get(coin)
        if last!=action:
            send_telegram_message(
                f"⚠️ **{coin} Action Changed**\n"
                f"New Avg Sentiment: {sentiment:.2f}\n"
                f"Suggested Action: {action}"
            )
            previous_actions[coin] = action

save_previous_actions(previous_actions)

# — Bar chart by coin & source —
if os.path.exists(chart_path):
    st.image(chart_path, caption="Sentiment by Coin and Source", use_container_width=True)

# — Trends Over Time —
st.markdown("<h3 style='color: var(--text-color);'>📈 Trends Over Time</h3>", unsafe_allow_html=True)
if not history.empty:
    last_update   = pd.to_datetime(history["Timestamp"], errors="coerce").max()
    days_of_data  = history["Timestamp"].str[:10].nunique()
    avg_all       = history["Sentiment"].mean()

    st.markdown(f"""
    <div style='padding:1rem;border:1px solid #444;border-radius:8px;
                margin-bottom:1rem;background-color:rgba(255,255,255,0.05);'>
      <b>📅 Last Updated:</b> {last_update}<br>
      <b>📊 Days of History:</b> {days_of_data}<br>
      <b>📈 Avg Sentiment (All):</b> {avg_all:.2f}
    </div>
    """, unsafe_allow_html=True)

    sel = st.selectbox("Select coin for trend view:", sorted(history["Coin"].dropna().unique()))
    ch  = history[history["Coin"]==sel]
    if not ch.empty:
        fig, ax1 = plt.subplots(figsize=(10,5))
        ax1.plot(ch["Timestamp"], ch["Sentiment"], marker="o", color="#1f77b4")
        ax1.set_ylabel("Sentiment", color="#1f77b4"); ax1.tick_params(labelcolor="#1f77b4")

        if "PriceUSD" in ch.columns:
            ax2 = ax1.twinx()
            ax2.plot(ch["Timestamp"], ch["PriceUSD"], linestyle="--", color="#2ca02c")
            ax2.set_ylabel("Price (USD)", color="#2ca02c"); ax2.tick_params(labelcolor="#2ca02c")

        ax1.set_xlabel("Time"); fig.autofmt_xdate()
        plt.title(f"{sel} — Sentiment & Price Over Time")
        st.pyplot(fig)
    else:
        st.info("No historical data yet for this coin.")
else:
    st.warning("📉 No historical trend data available.")

# — Sentiment Details Table (de-duplicated) —
st.subheader("📋 Sentiment Details")
coin_filter = st.selectbox("Filter by coin:", ["All"] + sorted(data["Coin"].dropna().unique()))
filt = data if coin_filter=="All" else data[data["Coin"]==coin_filter]
cols = ["Source","Sentiment","Action","Text","Link"]
avail = [c for c in cols if c in filt.columns]
if not filt.empty and avail:
    st.dataframe(filt[avail].sort_values("Sentiment", ascending=False))
else:
    st.info("No sentiment data to display.")
