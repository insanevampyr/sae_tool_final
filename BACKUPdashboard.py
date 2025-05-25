import json
import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime, timedelta
from dateutil import parser

from fetch_historical_prices import get_hourly_history
from fetch_prices import fetch_prices
from train_price_predictor import predict_prices

# ─── Configuration ─────────────────────────────────────────────────────
COINS         = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
HISTORY_DAYS  = 7
PRED_LOG_JSON = "prediction_log.json"
SENT_HIST_CSV = "sentiment_history.csv"
WINDOW_HOURS  = 24

# ─── Streamlit Setup ───────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="AlphaPulse Dashboard")

# ─── Header ────────────────────────────────────────────────────────────
st.markdown("<div style='text-align:center'>", unsafe_allow_html=True)
st.image("alpha_logo.jpg", width=200)
st.markdown("</div>", unsafe_allow_html=True)
st.markdown("## AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("Real price history + sentiment trends + next-hour forecasts")

# ─── Load Sentiment Data ───────────────────────────────────────────────
@st.cache_data
def load_sentiment():
    df = pd.read_csv(SENT_HIST_CSV)
    # Parse ISO8601 and strip timezone
    df["Timestamp"] = (
        df["Timestamp"]
          .apply(parser.isoparse)
          .apply(lambda dt: dt.replace(tzinfo=None))
    )
    return df

sent_df = load_sentiment()

# ─── Sidebar: 24h Sentiment Summary ─────────────────────────────────────
st.sidebar.markdown("### Sentiment Summary (24h)")
cut24 = datetime.utcnow() - timedelta(hours=24)
for coin in COINS:
    vals = sent_df[(sent_df.Coin == coin) & (sent_df.Timestamp >= cut24)]["Sentiment"]
    avg  = vals.mean() if not vals.empty else 0.0
    st.sidebar.metric(label=coin, value=f"{avg:.3f}")

# ─── Cached Loaders ────────────────────────────────────────────────────
@st.cache_data
def load_price_history(coin: str) -> pd.DataFrame:
    df = get_hourly_history(coin, days=HISTORY_DAYS)
    df["Timestamp"] = df["Timestamp"].apply(lambda dt: dt.replace(tzinfo=None))
    return df.set_index("Timestamp").resample("1h").ffill().bfill()

@st.cache_data(ttl=300)
def load_current_prices() -> dict:
    df = fetch_prices(COINS)
    return df.set_index("Coin")["PriceUSD"].to_dict()

# ─── Load Data ─────────────────────────────────────────────────────────
with st.spinner("Loading data…"):
    price_histories = {c: load_price_history(c) for c in COINS}
    curr_map        = load_current_prices()

# ─── Main: Trends Over Time ─────────────────────────────────────────────
coin = st.selectbox("Select coin for trends", COINS)
st.markdown(f"### Trends Over Time: {coin}")

price_df  = price_histories[coin]
raw_sent  = sent_df[sent_df.Coin == coin].set_index("Timestamp")["Sentiment"]
hourly    = raw_sent.resample("1h").mean()
aligned   = hourly.reindex(price_df.index, fill_value=0)

chart_df  = price_df.copy()
chart_df["Sentiment"] = aligned

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=chart_df.index, y=chart_df.PriceUSD,
    name="Price (USD)", yaxis="y1"
))
fig.add_trace(go.Scatter(
    x=chart_df.index, y=chart_df.Sentiment,
    name="Avg Sentiment", yaxis="y2"
))
fig.update_layout(
    xaxis=dict(rangeslider=dict(visible=True)),
    yaxis=dict(title="Price (USD)"),
    yaxis2=dict(
        title="Avg Sentiment", overlaying="y", side="right",
        rangemode="tozero"
    ),
    margin=dict(l=60, r=60, t=50, b=50)
)
st.plotly_chart(fig, use_container_width=True)

# ─── Main: Next-Hour Predictions ────────────────────────────────────────
st.markdown("### Next-Hour Predictions")
with open(PRED_LOG_JSON) as f:
    logs = json.load(f)

records = []
for c in COINS:
    entry = (logs.get(c) or [{}])[0]
    curr  = entry.get("current", curr_map.get(c))
    pred  = entry.get("predicted")
    if curr is not None and pred is not None:
        pct = round((pred - curr) / curr * 100, 2)
        pct_str = f"{pct:+.2f}%"
    else:
        pct_str = "N/A"

    records.append({
        "Coin":            c,
        "Current Price":   f"${curr:,.2f}"   if curr is not None else "N/A",
        "Predicted Price": f"${pred:,.2f}"   if pred is not None else "N/A",
        "% Change":        pct_str
    })

df_pred = pd.DataFrame(records).set_index("Coin")
st.table(df_pred)