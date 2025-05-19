import streamlit as st
import pandas as pd
from fetch_prices import fetch_prices
from fetch_historical_prices import get_hourly_history  # writes 7-day UTC history
from train_price_predictor import predict_prices

st.set_page_config(layout="wide")
COINS = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
HISTORY_DAYS = 7

@st.cache_data
def load_sentiment():
    df = pd.read_csv("sentiment_history.csv")
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True).dt.tz_convert(None)
    return df

@st.cache_data
def load_history(coin):
    df = get_hourly_history(coin, days=HISTORY_DAYS)  # returns columns ["timestamp","price"]
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(None)
    return df.set_index("timestamp")

sent_df = load_sentiment()
current_prices = fetch_prices(COINS).set_index("Coin")["PriceUSD"].to_dict()

tabs = st.tabs(["📊 Sentiment Summary", "📈 Trends Over Time", "🔮 Next Hour Predictions"])
with tabs[0]:
    st.markdown("## Sentiment Summary (last 24 hrs)")
    now = pd.Timestamp.utcnow()
    cutoff = now - pd.Timedelta(hours=24)
    recent = sent_df[sent_df.Timestamp >= cutoff]
    summary = recent.groupby("Coin")["Sentiment"].mean().round(3).reset_index()
    summary.columns = ["Coin", "Avg Sentiment"]
    st.table(summary)

with tabs[1]:
    coin = st.selectbox("Select coin", COINS, index=0)
    hist = load_history(coin)
    # pivot sentiment into hourly index
    hrs = pd.date_range(hist.index.min(), hist.index.max(), freq="H")
    sent_hourly = sent_df[sent_df.Coin == coin].set_index("Timestamp") \
                   .resample("H")["Sentiment"].mean().reindex(hrs).fillna(0.0)
    chart_df = pd.DataFrame({
        "PriceUSD": hist["price"].reindex(hrs),
        "Sentiment": sent_hourly
    }, index=hrs)
    st.markdown(f"## {coin} — Price vs Sentiment")
    st.line_chart(chart_df)

with tabs[2]:
    st.markdown("## Next Hour Predictions")
    now = pd.Timestamp.utcnow()
    cutoff = now - pd.Timedelta(hours=24)
    # rebuild avg sentiments
    avg_sents = {
        c: sent_df[(sent_df.Coin==c) & (sent_df.Timestamp>=cutoff)]["Sentiment"].mean() or 0.0
        for c in COINS
    }
    preds = predict_prices(avg_sents)

    rows = []
    for c in COINS:
        curr = current_prices.get(c, 0.0)
        p = preds.get(c, 0.0) or 0.0
        pct = (p - curr) / curr * 100 if curr else 0.0
        rows.append({
            "Coin": c,
            "Current Price": f"${curr:,.2f}",
            "Predicted Price": f"${p:,.2f}",
            "% Change": f"{pct:+.2f}%",
        })
    st.table(pd.DataFrame(rows))

