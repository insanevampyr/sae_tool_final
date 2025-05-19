# dashboard.py

import json
import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from dateutil import parser
import plotly.graph_objs as go

from fetch_historical_prices import get_hourly_history
from fetch_prices import fetch_prices

# ─── CONFIG ─────────────────────────────────────────────────────────
COINS         = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
SENT_HIST_CSV = "sentiment_history.csv"
PRED_LOG_JSON = "prediction_log.json"
HISTORY_DAYS  = 7    # days of history to fetch
WINDOW_HOURS  = 3    # for prediction context

st.set_page_config(layout="wide")

# ─── HEADER ─────────────────────────────────────────────────────────
st.markdown("<div style='text-align:center'>", unsafe_allow_html=True)
st.image("alpha_logo.jpg", width=200)
st.markdown("</div>", unsafe_allow_html=True)
st.markdown("## AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("Real price history + sentiment trends + next-hour forecasts")

# ─── CACHED LOADERS ─────────────────────────────────────────────────
@st.cache_data
def load_sentiment() -> pd.DataFrame:
    df = pd.read_csv(SENT_HIST_CSV)
    df["Timestamp"] = df["Timestamp"].apply(parser.isoparse)
    return df

@st.cache_data
def load_price_history(coin: str) -> pd.DataFrame:
    df = get_hourly_history(coin, days=HISTORY_DAYS)
    return df.set_index("Timestamp").resample("1h").ffill().bfill()

@st.cache_data
def load_current_prices(coins) -> dict:
    df = fetch_prices(coins)
    return df.set_index("Coin")["PriceUSD"].to_dict()

# ─── DATA INITIALIZATION ────────────────────────────────────────────
sent_df = load_sentiment()

# Preload all price histories once, for faster coin-switching
with st.spinner("Loading historical price data..."):
    price_histories = {c: load_price_history(c) for c in COINS}

curr_map = load_current_prices(COINS)

# ─── SIDEBAR: 24h SENTIMENT SUMMARY ─────────────────────────────────
st.sidebar.markdown("### Sentiment Summary (24h)")
cut24 = datetime.now(timezone.utc) - timedelta(hours=24)
for coin in COINS:
    vals = sent_df[(sent_df.Coin == coin) & (sent_df.Timestamp >= cut24)]["Sentiment"]
    avg  = vals.mean() if not vals.empty else 0.0
    st.sidebar.metric(label=coin, value=f"{avg:.3f}")

# ─── MAIN: TRENDS OVER TIME ───────────────────────────────────────────
coin = st.selectbox("Select coin for trends", COINS)
st.markdown(f"### Trends Over Time: {coin}")

price_df = price_histories[coin]

# Resample sentiment and zero-fill
sent_hourly = (
    sent_df[sent_df.Coin == coin]
        .set_index("Timestamp")["Sentiment"]
        .resample("1h")
        .mean()
        .fillna(0)
)

# Combine for plotting
df_chart = pd.concat([price_df, sent_hourly], axis=1)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df_chart.index, y=df_chart.PriceUSD,
    name="Price (USD)", yaxis="y1"
))
fig.add_trace(go.Scatter(
    x=df_chart.index, y=df_chart.Sentiment,
    name="Avg Sentiment", yaxis="y2"
))
fig.update_layout(
    xaxis=dict(rangeslider=dict(visible=True)),
    yaxis=dict(title="Price (USD)", side="left"),
    yaxis2=dict(title="Avg Sentiment", overlaying="y", side="right"),
    margin=dict(l=60, r=60, t=50, b=50)
)
st.plotly_chart(fig, use_container_width=True)

# ─── NEXT-HOUR PREDICTIONS ───────────────────────────────────────────
st.markdown("### Next-Hour Predictions")
with open(PRED_LOG_JSON) as f:
    log = json.load(f)

records = []
for c in COINS:
    entry = log.get(c, [{}])[0]
    curr = entry.get("current", curr_map.get(c))
    pred = entry.get("predicted")

    # compute % change only
    if curr is not None and pred is not None:
        pct = round((pred - curr) / curr * 100, 2)
        pct_str = f"{pct:+.2f}%"
    else:
        pct_str = "N/A"

    records.append({
        "Coin":            c,
        "Current Price":   f"${curr:,.2f}"   if curr is not None else "N/A",
        "Predicted Price": f"${pred:,.2f}"  if pred is not None else "N/A",
        "% Change":        pct_str
    })


df_pred = pd.DataFrame(records).set_index("Coin")
st.table(df_pred)
