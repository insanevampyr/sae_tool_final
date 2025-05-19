# dashboard.py
import os, json
import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from dateutil import parser
import plotly.graph_objs as go

# Local imports
from fetch_prices import fetch_prices

# Configuration
COINS = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
SENT_HIST_CSV = "sentiment_history.csv"
PRED_LOG_JSON  = "prediction_log.json"
WINDOW_HOURS   = 3  # for sentiment averaging

st.set_page_config(layout="wide")

# ─── Header ─────────────────────────────────────────────────────────────────
st.markdown("<div style='text-align:center'>", unsafe_allow_html=True)
st.image("alpha_logo.jpg", width=200)
st.markdown("</div>", unsafe_allow_html=True)
st.markdown("## AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("> ML-based next-hour prediction for each coin")

# ─── Load sentiment history ─────────────────────────────────────────────────
@st.cache_data
def load_sentiment():
    df = pd.read_csv(SENT_HIST_CSV)
    # robust ISO8601 parsing
    df["Timestamp"] = df["Timestamp"].apply(parser.isoparse)
    return df

data = load_sentiment()

# ─── Sidebar: 24h Sentiment Summary ────────────────────────────────────────
st.sidebar.markdown("### Sentiment Summary (24h)")
cutoff24 = datetime.now(timezone.utc) - timedelta(hours=24)
for coin in COINS:
    vals = data[(data.Coin == coin) & (data.Timestamp >= cutoff24)]["Sentiment"]
    avg  = vals.mean() if not vals.empty else 0.0
    st.sidebar.metric(label=coin, value=f"{avg:.3f}")

# ─── Trends Over Time ───────────────────────────────────────────────────────
coin = st.selectbox("Select coin for trends", COINS)
st.markdown(f"### Trends Over Time: {coin}")
subset = (
    data[data.Coin == coin]
    .set_index("Timestamp")
    .resample("1h")
    .agg({"PriceUSD": "last", "Sentiment": "mean"})
    .ffill()            # forward-fill last known price
    .interpolate()      # smooth sentiment
)

fig = go.Figure()
fig.add_trace(go.Scatter(x=subset.index, y=subset.PriceUSD,  name="Price (USD)",   yaxis="y1"))
fig.add_trace(go.Scatter(x=subset.index, y=subset.Sentiment, name="Avg Sentiment", yaxis="y2"))
fig.update_layout(
    xaxis = dict(rangeslider=dict(visible=True)),
    yaxis = dict(title="Price (USD)", side="left"),
    yaxis2= dict(title="Avg Sentiment", overlaying="y", side="right"),
    margin = dict(l=60, r=60, t=50, b=50),
)
st.plotly_chart(fig, use_container_width=True)

# ─── Next-Hour Predictions ────────────────────────────────────────────────
st.markdown("### Next-Hour Predictions")

# Load the last logged prediction per coin
with open(PRED_LOG_JSON) as f:
    log = json.load(f)

records = []
cutoff_pred = datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)
for coin in COINS:
    entries = log.get(coin, [])
    entry  = entries[0] if entries else {}
    current   = entry.get("current")
    predicted = entry.get("predicted")
    pct       = entry.get("diff_pct")

    # context: avg sentiment over the same window
    vals = data[(data.Coin == coin) & (data.Timestamp >= cutoff_pred)]["Sentiment"]
    avg_sent = vals.mean() if not vals.empty else None

    records.append({
        "Current Price"  : f"${current:,.2f}"    if current   is not None else "N/A",
        "Predicted Price": f"${predicted:,.2f}"  if predicted is not None else "N/A",
        "% Change"       : f"{pct:.2f}%"         if pct       is not None else "N/A",
        "Avg Sentiment"  : f"{avg_sent:.3f}"     if avg_sent is not None else "N/A",
    })

df_pred = pd.DataFrame(records, index=COINS)
st.table(df_pred)
