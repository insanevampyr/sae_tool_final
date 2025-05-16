# dashboard.py
from dotenv import load_dotenv
load_dotenv()

import os
import json
from datetime import datetime, timezone
import pandas as pd
import streamlit as st

# ─── CONFIG ────────────────────────────────────────────────────────────────
COINS         = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
HIST_CSV      = "sentiment_history.csv"
PRED_LOG_JSON = "prediction_log.json"

# ─── HELPERS ───────────────────────────────────────────────────────────────
@st.cache_data
def load_history() -> pd.DataFrame:
    if not os.path.exists(HIST_CSV):
        return pd.DataFrame(columns=[
            'Timestamp','Coin','Source','Sentiment','PriceUSD','SuggestedAction'
        ])
    df = pd.read_csv(HIST_CSV, parse_dates=["Timestamp"], infer_datetime_format=True)
    # ensure timezone-aware
    if df.Timestamp.dt.tz is None:
        df.Timestamp = df.Timestamp.dt.tz_localize("UTC")
    return df

@st.cache_data
def load_predictions() -> dict:
    if not os.path.exists(PRED_LOG_JSON):
        return {c: [] for c in COINS}
    return json.loads(open(PRED_LOG_JSON, "r", encoding="utf-8").read())

# ─── LAYOUT ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AlphaPulse", layout="wide")
st.sidebar.header("📌 Sentiment Summary")

# 1) window selector
window = st.sidebar.selectbox(
    "Summary window",
    ["Last 24 Hours", "Last 7 Days", "Last 30 Days"],
    index=0
)

# 2) load and slice
hist = load_history()
now = datetime.now(timezone.utc)
if window == "Last 24 Hours":
    cutoff = now - pd.Timedelta(hours=24)
elif window == "Last 7 Days":
    cutoff = now - pd.Timedelta(days=7)
else:
    cutoff = now - pd.Timedelta(days=30)
recent = hist[hist.Timestamp >= cutoff]

# 3) freshness
if hist.empty:
    st.sidebar.info("No data yet.")
else:
    st.sidebar.info(f"Data newest at {hist.Timestamp.max()}")

# 4) per‐coin summary
for coin in COINS:
    dfc = recent[recent.Coin == coin]
    avg = dfc.Sentiment.mean() if not dfc.empty else float("nan")
    action = "🤝 Hold" if abs(avg) < 0.2 else ("📈 Buy" if avg > 0 else "📉 Sell")
    color = "green" if avg > 0 else ("red" if avg < 0 else "black")
    st.sidebar.markdown(f"**{coin}**: <span style='color:{color}'>{avg:+.3f}</span> → {action}", unsafe_allow_html=True)

# ─── MAIN ──────────────────────────────────────────────────────────────────
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")

# 5) ML Price Predictions (unchanged)
st.subheader("🤖 Next-Hour Price Forecasts")
plog = load_predictions()
for coin in COINS:
    entries = plog.get(coin, [])
    if entries:
        last = entries[-1]
        pred = last.get("predicted", 0)
        ts   = last.get("timestamp", "–")
        acc  = last.get("accurate", None)
        st.markdown(
            f"**{coin}**  •  “now” ${last.get('current', 0):.2f}  →  **{pred:.2f}** by {ts[-5:]} UTC  "
            + (f"<span style='color:green'>▲</span>" if pred > last.get('current',0)
               else f"<span style='color:red'>▼</span>") 
            + (f"  •  {acc*100:.0f}% acc (24h)" if acc is not None else ""),
            unsafe_allow_html=True
        )
    else:
        st.markdown(f"**{coin}** → No prediction yet.")

# 6) Trends Over Time: overlay Sentiment & PriceUSD
st.subheader("📈 Trends Over Time")
coin = st.selectbox("Select coin:", COINS)
dfc = hist[hist.Coin == coin].set_index("Timestamp").sort_index()
if dfc.empty:
    st.info("No historical data for this coin yet.")
else:
    dfc = dfc[["Sentiment","PriceUSD"]]
    dfc.columns = ["Sentiment","Price (USD)"]
    st.line_chart(dfc, use_container_width=True)

# 7) Footer
if not hist.empty:
    st.caption(f"Last updated: {hist.Timestamp.max()} UTC")
