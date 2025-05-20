import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os

COINS = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
HISTORY_DAYS = 7

st.set_page_config(page_title="AlphaPulse Dashboard", layout="wide")

# --- Loaders ---
@st.cache_data(show_spinner=False)
def load_price_history(coin):
    # For more coins: change to e.g. "eth_history.csv" if you export per coin
    df = pd.read_csv("btc_history.csv")  
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df = df[df["Coin"].str.lower() == coin.lower()]
    df = df.set_index("Timestamp").resample("h").mean()
    return df

@st.cache_data(show_spinner=False)
def load_sentiment_history():
    df = pd.read_csv("sentiment_history.csv")
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    return df

def get_sentiment_last_24h(df, coin):
    now = pd.Timestamp.utcnow()
    last_24h = df[(df["Coin"].str.lower() == coin.lower()) & (df["Timestamp"] >= now - pd.Timedelta("24h"))]
    return last_24h["Sentiment"].mean() if not last_24h.empty else 0

# --- UI ---
st.title("AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("###")
tab1, tab2, tab3 = st.tabs(["Sentiment Summary", "Trends Over Time", "Next Hour Predictions"])

with tab1:
    st.markdown("#### Sentiment Summary (24h)")
    sentiment = load_sentiment_history()
    cols = st.columns(len(COINS))
    for i, coin in enumerate(COINS):
        val = get_sentiment_last_24h(sentiment, coin)
        cols[i].markdown(f"**{coin}**")
        cols[i].markdown(f"<h2>{val:+.3f}</h2>", unsafe_allow_html=True)

with tab2:
    st.markdown("####")
    coin = st.selectbox("Select coin", COINS, key="trends_coin")
    hist = load_price_history(coin)
    sentiment = load_sentiment_history()
    coin_sent = sentiment[sentiment["Coin"].str.lower() == coin.lower()]
    coin_sent = coin_sent.set_index("Timestamp").resample("h")["Sentiment"].mean()
    plot_data = hist.join(coin_sent, how="outer")

    fig = go.Figure()
    # Price trace
    fig.add_trace(go.Scatter(
        x=plot_data.index, y=plot_data["PriceUSD"], name="Price (USD)", yaxis="y1"
    ))
    # Sentiment trace
    fig.add_trace(go.Scatter(
        x=plot_data.index, y=plot_data["Sentiment"], name="Avg Sentiment", yaxis="y2"
    ))
    fig.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=24, label="1d", step="hour", stepmode="backward"),
                    dict(count=72, label="3d", step="hour", stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(visible=True),  # draggable scroll bar
            type="date"
        ),
        yaxis=dict(
            title="Price (USD)",
            side="left"
        ),
        yaxis2=dict(
            title="Avg Sentiment",
            overlaying="y",
            side="right"
        ),
        legend=dict(x=0, y=1.1, orientation="h"),
        title=f"{coin} — Price vs Sentiment (Last {HISTORY_DAYS} Days)"
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("#### Next Hour Predictions")
    # Display your predictions table as before (assuming you have a DataFrame for it)
    if os.path.exists("prediction_log.json"):
        with open("prediction_log.json") as f:
            log = json.load(f)
        data = []
        for coin in COINS:
            entries = log.get(coin, [])
            if not entries:
                continue
            latest = entries[-1]
            accs = [x.get("accurate") for x in entries[-24:] if x.get("accurate") is not None]
            if accs:
                accs = [int(a) for a in accs if a is not None]
                accuracy = int(sum(accs) / len(accs) * 100) if accs else 0
            else:
                accuracy = 0
            data.append({
                "Coin": coin,
                "Current": latest.get("actual"),
                "Predicted": latest.get("predicted"),
                "Δ %": f"{latest.get('diff_pct', 0):+.1f}%",
                "24h Acc": f"{accuracy}%"
            })
        st.dataframe(pd.DataFrame(data))
    else:
        st.info("prediction_log.json not found.")
