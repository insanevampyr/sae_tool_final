# dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json, os
from datetime import datetime, timezone
from send_telegram      import send_telegram_message
from reddit_fetch       import fetch_reddit_posts
from rss_fetch          import fetch_rss_articles
from analyze_sentiment  import analyze_sentiment
from fetch_prices       import fetch_prices

st.set_page_config(page_title="AlphaPulse | Sentiment Dashboard", layout="wide")

# — Branding —
st.image("alpha_logo.jpg", use_container_width=True)
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("Live crypto sentiment analysis from Reddit and news + historical trends.")

# — File paths —
CSV_PATH     = "sentiment_output.csv"
CHART_PATH   = "sentiment_chart.png"
HISTORY_PATH = "sentiment_history.csv"
JSON_PATH    = "previous_actions.json"

def load_csv(path):
    """Load a CSV skipping bad lines, return empty DF on error."""
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(
            path,
            engine="python",
            on_bad_lines="skip",
            dtype=str  # read everything as string first
        )
    except Exception as e:
        st.error(f"Failed to load {path}: {e}")
        return pd.DataFrame()

def load_previous_actions():
    if os.path.exists(JSON_PATH):
        return json.load(open(JSON_PATH))
    return {}

def save_previous_actions(d):
    json.dump(d, open(JSON_PATH, "w"))

# — Load & sanitize sentiment data —
data = load_csv(CSV_PATH)

if not data.empty:
    # only keep rows with Coin & Sentiment
    data = data.dropna(subset=["Coin","Sentiment"])
    # coerce Sentiment to float, drop invalid
    data["Sentiment"] = pd.to_numeric(data["Sentiment"], errors="coerce")
    data = data.dropna(subset=["Sentiment"])
    # drop exact duplicates
    data = data.drop_duplicates(
        subset=["Source","Coin","Text","Link","Timestamp"],
        keep="first"
    )

history = load_csv(HISTORY_PATH)
previous_actions = load_previous_actions()
prices = fetch_prices()

# — Sidebar: summary & toggles —
st.sidebar.header("📌 Sentiment Summary")

if data.empty:
    st.sidebar.warning("No sentiment data available.")
else:
    overall = data.groupby("Coin")["Sentiment"].mean()
    for coin, sentiment in overall.items():
        action    = "📈 Buy" if sentiment>0.2 else "📉 Sell" if sentiment<-0.2 else "🤝 Hold"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        st.sidebar.write(f"**{coin}**: {sentiment:.2f} → {action}")
        st.sidebar.caption(f"_Updated: {timestamp}_")

        key = f"alert_toggle_{coin}"
        if st.sidebar.checkbox(f"🔔 Alert for {coin}", key=key):
            last = previous_actions.get(coin)
            if last != action:
                send_telegram_message(
                    f"⚠️ **{coin} Action Changed**\n"
                    f"New Avg Sentiment: {sentiment:.2f}\n"
                    f"Suggested Action: {action}"
                )
                previous_actions[coin] = action

save_previous_actions(previous_actions)

# — Bar chart by coin & source —
if os.path.exists(CHART_PATH):
    st.image(CHART_PATH, caption="Sentiment by Coin and Source", use_container_width=True)

# — Trends Over Time —
st.markdown("<h3 style='color: var(--text-color);'>📈 Trends Over Time</h3>", unsafe_allow_html=True)

if history.empty:
    st.warning("📉 No historical trend data available.")
else:
    # sanitize history like above
    history = history.dropna(subset=["Coin","Sentiment","Timestamp"])
    history["Sentiment"] = pd.to_numeric(history["Sentiment"], errors="coerce")
    history = history.dropna(subset=["Sentiment"])
    history = history.sort_values("Timestamp")

    last_update  = pd.to_datetime(history["Timestamp"], errors="coerce").max()
    days_of_data = history["Timestamp"].str[:10].nunique()
    avg_all      = history["Sentiment"].mean()

    st.markdown(f"""
    <div style="
      padding:1rem;
      border:1px solid #444;
      border-radius:8px;
      margin-bottom:1rem;
      background-color:rgba(255,255,255,0.05);
      color: var(--text-color);
    ">
      <b>📅 Last Updated:</b> {last_update}<br>
      <b>📊 Days of History:</b> {days_of_data}<br>
      <b>📈 Avg Sentiment (All):</b> {avg_all:.2f}
    </div>
    """, unsafe_allow_html=True)

    sel = st.selectbox("Select coin for trend view:", sorted(history["Coin"].unique()))
    ch  = history[history["Coin"]==sel]

    if ch.empty:
        st.info("No historical data yet for this coin.")
    else:
        fig, ax1 = plt.subplots(figsize=(10,5))
        ax1.plot(ch["Timestamp"], ch["Sentiment"], marker="o", color="#1f77b4")
        ax1.set_ylabel("Sentiment", color="#1f77b4")
        ax1.tick_params(labelcolor="#1f77b4")
        ax1.set_xlabel("Time")

        if "PriceUSD" in ch.columns:
            ax2 = ax1.twinx()
            ax2.plot(ch["Timestamp"], ch["PriceUSD"], linestyle="--", color="#2ca02c")
            ax2.set_ylabel("Price (USD)", color="#2ca02c")
            ax2.tick_params(labelcolor="#2ca02c")

        plt.title(f"{sel} — Sentiment & Price Over Time")
        fig.autofmt_xdate()
        st.pyplot(fig)

# — Sentiment Details Table —
st.subheader("📋 Sentiment Details")
if data.empty:
    st.info("No sentiment data to display.")
else:
    coin_filter = st.selectbox("Filter by coin:", ["All"] + sorted(data["Coin"].unique()))
    filt = data if coin_filter=="All" else data[data["Coin"]==coin_filter]
    cols = ["Source","Sentiment","Action","Text","Link"]
    avail = [c for c in cols if c in filt.columns]
    st.dataframe(filt[avail].sort_values("Sentiment", ascending=False))
