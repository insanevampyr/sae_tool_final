import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
from datetime import datetime, timezone

PRED_LOG        = "prediction_log.json"
SENT_HIST_CSV   = "sentiment_history.csv"

@st.cache_data
def load_sentiment_history():
    df = pd.read_csv(SENT_HIST_CSV)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, format="mixed")
    return df

@st.cache_data
def load_predictions():
    with open(PRED_LOG, "r") as f:
        raw = json.load(f)
    records = []
    for entry in raw:
        # ensure we have a dict
        if not isinstance(entry, dict):
            continue
        records.append({
            "coin":      entry.get("coin"),
            "timestamp": entry.get("timestamp"),
            "current":   entry.get("current_price"),
            "predicted": entry.get("predicted_price"),
            "accuracy":  entry.get("accurate")
        })
    return pd.DataFrame(records)

st.title("🔮 Crypto Sentiment & Forecast Dashboard")

# Sidebar: Sentiment Summary
window = st.sidebar.selectbox("Sentiment window", ["1H","24H","7D"])
hist = load_sentiment_history().set_index("Timestamp")
summary = hist.last(window).groupby("Coin")["Sentiment"].agg(["mean","count"])
st.sidebar.markdown("## Sentiment Summary")
if summary.empty:
    st.sidebar.write("No data for that window.")
else:
    for coin, row in summary.iterrows():
        avg = row["mean"]
        cnt = int(row["count"])
        action = "BUY" if avg>0.05 else ("SELL" if avg< -0.05 else "HOLD")
        st.sidebar.write(f"**{coin}**: {avg:+.3f} ({cnt} msgs) → {action}")

# Next-Hour Price Forecasts
st.header("⏳ Next-Hour Price Forecasts")
preds = load_predictions()
if preds.empty:
    st.write("No prediction data yet.")
else:
    # show latest per coin
    latest = preds.sort_values("timestamp").groupby("coin").tail(1)
    cols = st.columns(len(latest))
    for col, (_, r) in zip(cols, latest.iterrows()):
        curr = r["current"]
        pred = r["predicted"]
        acc  = r["accuracy"]
        change = (pred/curr - 1)*100 if curr and pred else None
        color = "green" if change and change>0 else "red"
        col.markdown(f"### {r['coin']}")
        col.metric("Now", f"${curr:.2f}" if curr else "–",
                   f"{change:+.2f}%" if change else "–", delta_color=color)
        col.write(f"Predicted: **${pred:.2f}**  \nAccuracy: **{acc*100:.0f}%**" if acc is not None else "")

# Trends Over Time
st.header("📈 Trends Over Time")
coin = st.selectbox("Select coin", hist["Coin"].unique())
dfc = hist[hist["Coin"]==coin].resample("1H").agg({
    "PriceUSD": "last",
    "Sentiment":"mean"
}).interpolate()
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=dfc.index, y=dfc["PriceUSD"], name="Price (USD)", yaxis="y1"))
fig.add_trace(go.Scatter(
    x=dfc.index, y=dfc["Sentiment"], name="Sentiment", yaxis="y2"))
fig.update_layout(
    xaxis=dict(rangeslider=dict(visible=True)),
    yaxis=dict(title="Price (USD)"),
    yaxis2=dict(title="Sentiment", overlaying="y", side="right"),
    legend=dict(y=0.5, traceorder="reversed")
)
st.plotly_chart(fig, use_container_width=True)
