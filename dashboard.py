# dashboard.py
import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from dateutil import parser
import plotly.graph_objs as go
from fetch_prices import fetch_prices
from train_price_predictor import predict_prices

# Configuration
COINS = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
SENT_HIST_CSV = "sentiment_history.csv"
WINDOW_HOURS = 3  # hours back for computing sentiment

# Page setup
st.set_page_config(layout="wide")

# Header: Logo and Title
st.markdown("<div style='text-align:center'>", unsafe_allow_html=True)
st.image("alpha_logo.jpg", width=200)
st.markdown("</div>", unsafe_allow_html=True)
st.markdown("## AlphaPulse: Crypto Sentiment Dashboard")

# Sidebar: 24h Sentiment Summary
def load_sentiment():
    df = pd.read_csv(SENT_HIST_CSV)
    df["Timestamp"] = df["Timestamp"].apply(parser.isoparse)
    return df

@st.cache_data
def sentiment_data():
    return load_sentiment()

data = sentiment_data()
st.sidebar.markdown("### Sentiment Summary (24h)")
cutoff24 = datetime.now(timezone.utc) - timedelta(hours=24)
for coin in COINS:
    vals = data[(data.Coin == coin) & (data.Timestamp >= cutoff24)]["Sentiment"]
    avg = vals.mean() if not vals.empty else 0.0
    st.sidebar.metric(label=coin, value=f"{avg:.3f}")

# Main: Coin Selector & Trends
coin = st.selectbox("Select coin for trends", COINS)
st.markdown(f"### Trends Over Time: {coin}")
subset = (
    data[data.Coin == coin]
    .set_index("Timestamp")
    .resample("1h")
    .agg({"PriceUSD": "last", "Sentiment": "mean"})
    .interpolate()
)
fig = go.Figure()
fig.add_trace(go.Scatter(x=subset.index, y=subset.PriceUSD, name="Price (USD)", yaxis="y1"))
fig.add_trace(go.Scatter(x=subset.index, y=subset.Sentiment, name="Avg Sentiment", yaxis="y2"))
fig.update_layout(
    xaxis=dict(rangeslider=dict(visible=True)),
    yaxis=dict(title="Price (USD)", side="left"),
    yaxis2=dict(title="Avg Sentiment", overlaying="y", side="right"),
    legend=dict(x=0.01, y=0.99),
    margin=dict(l=60, r=60, t=50, b=50)
)
st.plotly_chart(fig, use_container_width=True)

# Next-Hour Predictions Summary
st.markdown("### Next-Hour Predictions")
# fetch current prices once
def load_current_prices():
    df = fetch_prices(COINS)
    return dict(zip(df.Coin, df.PriceUSD))

current_prices = load_current_prices()

records = []
cutoff_pred = datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)
for coin in COINS:
    # sentiment window
    window = data[(data.Coin == coin) & (data.Timestamp >= cutoff_pred)]["Sentiment"]
    if not window.empty:
        avg_sent = window.mean()
    else:
        recent_all = data[data.Coin == coin]
        avg_sent = recent_all.sort_values("Timestamp").iloc[-1].Sentiment if not recent_all.empty else None
    current = current_prices.get(coin)
    if avg_sent is not None and current is not None:
        predicted_label = predict_prices(pd.DataFrame({'AvgSentiment': [avg_sent]}))[0]
        predicted = current * (1.01 if predicted_label == 1 else 0.99)
        diff = (predicted - current) / current * 100
    else:
        predicted = None
        diff = None
    records.append({
        'Coin': coin,
        'Current Price': f"${current:,.2f}" if current is not None else "N/A",
        'Predicted Price': f"${predicted:,.2f}" if predicted is not None else "N/A",
        '% Change': f"{diff:.2f}%" if diff is not None else "N/A",
        'Avg Sentiment': f"{avg_sent:.3f}" if avg_sent is not None else "N/A"
    })

df_pred = pd.DataFrame(records).set_index('Coin')
st.table(df_pred)
