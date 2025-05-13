# dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import json
import os
from datetime import datetime, timezone, timedelta
from send_telegram import send_telegram_message
from reddit_fetch import fetch_reddit_posts
from rss_fetch import fetch_rss_articles
from analyze_sentiment import analyze_sentiment
from fetch_prices import fetch_prices

# — Page config & Branding —
st.set_page_config(page_title="AlphaPulse | Sentiment Dashboard", layout="wide")
st.image("alpha_logo.jpg", use_container_width=True)
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("Live crypto sentiment analysis from Reddit and news + historical trends.")

# — File paths —
csv_path     = "sentiment_output.csv"
chart_path   = "sentiment_chart.png"
history_file = "sentiment_history.csv"
json_path    = "previous_actions.json"

def load_data(path):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
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

# — Load datasets & credentials —
data    = load_data(csv_path)
history = load_data(history_file)
actions = load_previous_actions()
prices  = fetch_prices()

# — Sidebar: current sentiment & alert toggles —
st.sidebar.header("📌 Sentiment Summary")
if not data.empty:
    overall = data.groupby("Coin")["Sentiment"].mean()
    for coin, avg in overall.items():
        action = "📈 Buy" if avg > 0.2 else "📉 Sell" if avg < -0.2 else "🤝 Hold"
        ts     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        st.sidebar.write(f"**{coin}**: {avg:.2f} → {action}")
        st.sidebar.caption(f"_Updated: {ts}_")

        key = f"alert_toggle_{coin}"
        if st.sidebar.checkbox(f"🔔 Alert for {coin}", key=key):
            if actions.get(coin) != action:
                msg = f"⚠️ **{coin} Action Changed**\nNew Avg Sentiment: {avg:.2f}\n**Suggested Action:** {action}"
                send_telegram_message(msg)
                actions[coin] = action
    save_previous_actions(actions)
else:
    st.sidebar.info("No sentiment data found. Run `analyze.py` first.")

# — Latest-run bar chart —
if os.path.exists(chart_path):
    st.image(chart_path, caption="Sentiment by Coin and Source", use_container_width=True)

# — Trends Over Time (always visible) —
st.markdown("<h3 style='color: var(--primary-text-color);'>📈 Trends Over Time</h3>", unsafe_allow_html=True)

if not history.empty:
    # Clean & parse
    history.rename(columns=lambda c: c.strip(), inplace=True)
    history["Timestamp"] = pd.to_datetime(history["Timestamp"], errors="coerce")

    # Summary card
    last_upd     = history["Timestamp"].max()
    days_of_data = history["Timestamp"].dt.date.nunique()
    avg_all      = history["Sentiment"].mean()
    st.markdown(f"""
    <div style='padding:1rem; border:1px solid #444; border-radius:8px; margin-bottom:1rem;
                background-color:rgba(255,255,255,0.1);'>
      <b>📅 Last Updated:</b> {last_upd}<br>
      <b>📊 Days of History:</b> {days_of_data}<br>
      <b>📈 Avg Sentiment:</b> {avg_all:.2f}
    </div>
    """, unsafe_allow_html=True)

    # Time-range dropdown
    range_opt = st.selectbox(
        "Time range:",
        ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "Last 6 Months", "Last Year"],
        index=1
    )
    now = datetime.now(timezone.utc)
    cutoffs = {
        "Last 24 Hours": now - timedelta(days=1),
        "Last 7 Days": now - timedelta(days=7),
        "Last 30 Days": now - timedelta(days=30),
        "Last 6 Months": now - timedelta(days=182),
        "Last Year": now - timedelta(days=365)
    }
    cutoff = cutoffs[range_opt]

    # Coin selector & filter
    coin = st.selectbox("Select coin for trend view:", sorted(history["Coin"].dropna().unique()))
    df_c = history[(history["Coin"] == coin) & (history["Timestamp"] >= cutoff)]

    if not df_c.empty:
        fig, ax1 = plt.subplots(figsize=(10,5))
        locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
        fmt     = mdates.ConciseDateFormatter(locator)
        ax1.xaxis.set_major_locator(locator)
        ax1.xaxis.set_major_formatter(fmt)

        ax1.plot(df_c["Timestamp"], df_c["Sentiment"],
                 marker="o", color="#1f77b4", label="Sentiment")
        ax1.set_ylabel("Sentiment", color="#1f77b4")
        ax1.tick_params(axis='y', labelcolor="#1f77b4")
        ax1.set_xlabel("Time")

        if "PriceUSD" in df_c.columns:
            ax2 = ax1.twinx()
            ax2.plot(df_c["Timestamp"], df_c["PriceUSD"],
                     linestyle="--", color="#2ca02c", label="Price (USD)")
            ax2.set_ylabel("Price (USD)", color="#2ca02c")
            ax2.tick_params(axis='y', labelcolor="#2ca02c")

        plt.title(f"{coin} — Sentiment & Price Over Time")
        fig.autofmt_xdate()
        st.pyplot(fig)
    else:
        st.info("No history in that time window for this coin.")
else:
    st.warning("📉 No historical trend data available. Run `analyze.py` to build it.")

# — Sentiment Details Table —
st.subheader("📋 Sentiment Details")
if not data.empty:
    flt = st.selectbox("Filter by coin:", ["All"] + sorted(data["Coin"].unique()))
    view = data if flt == "All" else data[data["Coin"] == flt]
    cols = ["Source","Coin","Sentiment","Action","Text","Link"]
    available = [c for c in cols if c in view.columns]
    st.dataframe(
        view[available]
            .drop_duplicates()
            .sort_values("Sentiment", ascending=False),
        use_container_width=True
    )
else:
    st.info("No sentiment data to show.")
