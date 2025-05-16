import os
import pandas as pd
import streamlit as st
from fetch_prices import fetch_prices

# ─── CONFIG ────────────────────────────────────────────────────────────────
COINS = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
HIST_CSV = "sentiment_history.csv"

# ─── HELPERS ───────────────────────────────────────────────────────────────
@st.cache_data
def load_history():
    if not os.path.exists(HIST_CSV):
        return pd.DataFrame(columns=["Timestamp", "Coin", "Sentiment"])
    df = pd.read_csv(HIST_CSV, parse_dates=["Timestamp"], infer_datetime_format=True)
    # ensure UTC
    if df["Timestamp"].dt.tz is None:
        df["Timestamp"] = df["Timestamp"].dt.tz_localize("UTC")
    return df

# ─── LAYOUT ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AlphaPulse", layout="wide")
st.sidebar.header("📌 Sentiment Summary")

# 1) Time window selector
window = st.sidebar.selectbox(
    "Summary window",
    ["Last 24 Hours", "Last 7 Days", "Last 30 Days"],
    index=0,
)
hist = load_history()
now = pd.Timestamp.utcnow()

# 2) Compute cutoff
if window == "Last 24 Hours":
    cutoff = now - pd.Timedelta(hours=24)
elif window == "Last 7 Days":
    cutoff = now - pd.Timedelta(days=7)
else:
    cutoff = now - pd.Timedelta(days=30)

recent = hist[hist.Timestamp >= cutoff]

# 3) Freshness indicator
if hist.empty:
    st.sidebar.info("No data yet.")
else:
    last_ts = hist.Timestamp.max()
    st.sidebar.info(f"Data newest at {last_ts.strftime('%Y-%m-%d %H:%M UTC')}")

# 4) Per‐coin averages
for coin in COINS:
    dfc = recent[recent.Coin == coin]
    avg = dfc.Sentiment.mean() if not dfc.empty else 0.0
    if abs(avg) < 0.2:
        action = "🤝 Hold"
    elif avg > 0:
        action = "📈 Buy"
    else:
        action = "📉 Sell"
    st.sidebar.write(f"**{coin}:** {avg:+.3f} → {action}")

# ─── MAIN CONTENT ──────────────────────────────────────────────────────────
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")

# 5) Next‐Hour Price Forecasts
st.subheader("🤖 Next-Hour Price Forecasts")
prices = fetch_prices()  # no arguments here!
cols = st.columns(len(COINS))
for col, coin in zip(cols, COINS):
    current = prices.get(coin, 0.0)
    # placeholder for predicted: replace with real ML call if you have one
    predicted = current * 1.02  # e.g. placeholder +2%
    pct = (predicted - current) / current if current else 0
    color = "green" if pct > 0 else ("red" if pct < 0 else "black")
    with col:
        st.markdown(f"**{coin}**", unsafe_allow_html=True)
        st.write(f"Current: ${current:,.2f}")
        st.write(
            f"Predicted: <span style='color:{color}'>${predicted:,.2f} ({pct:+.1%})</span>",
            unsafe_allow_html=True,
        )

# 6) Trends Over Time
st.subheader("📈 Trends Over Time")
coin = st.selectbox("Select coin:", COINS)
series = hist[hist.Coin == coin].set_index("Timestamp")["Sentiment"]
st.line_chart(series)

# 7) Footer
if not hist.empty:
    st.caption(f"Last updated: {hist.Timestamp.max().strftime('%Y-%m-%d %H:%M UTC')}")
