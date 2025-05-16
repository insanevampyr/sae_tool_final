from dotenv import load_dotenv
load_dotenv()

import os, json
from datetime import datetime, timezone
import pandas as pd
import streamlit as st

# ─── CONFIG ────────────────────────────────────────────────────────────────
COINS         = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
HIST_CSV      = "sentiment_history.csv"
PRED_LOG_JSON = "prediction_log.json"

# ─── HELPERS ───────────────────────────────────────────────────────────────
@st.cache_data
def load_history():
    if not os.path.exists(HIST_CSV):
        return pd.DataFrame(columns=['Timestamp','Coin','Source','Sentiment','PriceUSD','SuggestedAction'])
    df = pd.read_csv(HIST_CSV, parse_dates=['Timestamp'])
    if df['Timestamp'].dt.tz is None:
        df['Timestamp'] = df['Timestamp'].dt.tz_localize('UTC')
    return df

@st.cache_data
def load_predictions():
    if not os.path.exists(PRED_LOG_JSON):
        return {c: [] for c in COINS}
    return json.load(open(PRED_LOG_JSON, 'r', encoding='utf-8'))

# ─── RENDER ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AlphaPulse", layout="wide")
st.sidebar.header("📌 Sentiment Summary")

# 1) Window selector
window = st.sidebar.selectbox(
    "Summary window",
    ["Last 24 Hours", "Last 7 Days", "Last 30 Days"],
    index=0
)

hist = load_history()
now = datetime.now(timezone.utc)

# 2) Compute cutoff
if window=="Last 24 Hours":
    cutoff = now - pd.Timedelta(hours=24)
elif window=="Last 7 Days":
    cutoff = now - pd.Timedelta(days=7)
else:
    cutoff = now - pd.Timedelta(days=30)

recent = hist[hist.Timestamp >= cutoff]

# 3) Freshness banner
if hist.empty:
    st.sidebar.info("No data yet.")
else:
    st.sidebar.info(f"Data newest at {hist.Timestamp.max()}")

# 4) Sidebar per‐coin averages
for coin in COINS:
    dfc = recent[recent.Coin==coin]
    avg = dfc.Sentiment.mean() if not dfc.empty else float('nan')
    action = "🤝 Hold" if abs(avg)<0.2 else ("📈 Buy" if avg>0 else "📉 Sell")
    st.sidebar.write(f"**{coin}**: {avg:+.3f} → {action}")

# ─── MAIN ──────────────────────────────────────────────────────────────────
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")

# 5) ML Predictions panel
st.subheader("🤖 ML Price Predictions")
plog = load_predictions()
for coin in COINS:
    ent = plog.get(coin, [])
    if ent:
        last = ent[-1]
        ts   = last.get('timestamp','–')
        pred = last.get('predicted',0)
        acc  = last.get('accurate',None)
        st.markdown(f"**{coin}** → Pred ${pred:.2f} @ {ts} UTC  • " +
                    ("✅" if acc else "⚠️"))
    else:
        st.markdown(f"**{coin}** → No prediction yet.")

# 6) Trends Over Time chart
st.subheader("📈 Trends Over Time")
coin = st.selectbox("Select coin:", COINS)
series = hist[hist.Coin==coin].set_index('Timestamp')['Sentiment']
st.line_chart(series)

# 7) Footer
if not hist.empty:
    st.caption(f"Last updated: {hist.Timestamp.max()}")
