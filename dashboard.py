import streamlit as st
import pandas as pd
import json, datetime
from dateutil import parser
import plotly.express as px

from fetch_prices import fetch_prices
from fetch_historical_prices import get_hourly_history

# ─── CONFIG ────────────────────────────────────────────────────────────────
COINS         = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
HIST_CSV      = "sentiment_history.csv"
PRED_LOG_JSON = "prediction_log.json"
HISTORY_DAYS  = 7

st.set_page_config(layout="wide")

@st.cache_data
def load_sentiment():
    df = pd.read_csv(HIST_CSV)
    def _parse(s):
        dt = parser.isoparse(s) if isinstance(s, str) else s
        if dt.tzinfo:
            dt = dt.astimezone(datetime.timezone.utc)
        return dt.replace(tzinfo=None)
    df["Timestamp"] = df["Timestamp"].apply(_parse)
    return df

@st.cache_data
def load_history(coin: str):
    df = get_hourly_history(coin, days=HISTORY_DAYS)
    def _parse(s):
        dt = parser.isoparse(s) if isinstance(s, str) else s
        if dt.tzinfo:
            dt = dt.astimezone(datetime.timezone.utc)
        return dt.replace(tzinfo=None)
    df["Timestamp"] = df["Timestamp"].apply(_parse)
    return df.set_index("Timestamp").rename(columns={"PriceUSD": "price"})

@st.cache_data
def load_current_prices():
    df = fetch_prices(COINS)
    return dict(zip(df["Coin"], df["PriceUSD"]))

@st.cache_data
def load_prediction_log():
    with open(PRED_LOG_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    st.image("alpha_logo.jpg", width=200)
    st.title("AlphaPulse: Crypto Sentiment Dashboard")

    sent_df        = load_sentiment()
    current_prices = load_current_prices()
    pred_log       = load_prediction_log()

    tabs = st.tabs(["Sentiment Summary", "Trends Over Time", "Next Hour Predictions"])

    # ─── 1) Sentiment Summary ───────────────────────────────────────────────
    with tabs[0]:
        st.header("Sentiment Summary (Last 24 h)")
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        summary = []
        for c in COINS:
            avg = (
                sent_df[(sent_df["Coin"]==c) & (sent_df["Timestamp"]>=cutoff)]
                  .Sentiment
                  .mean() or 0.0
            )
            summary.append({"Coin": c, "Avg Sentiment": round(avg,4)})
        st.table(pd.DataFrame(summary))

    # ─── 2) Trends Over Time ───────────────────────────────────────────────
    with tabs[1]:
        coin = st.selectbox("Select coin", COINS)
        hist = load_history(coin)

        # uniform hourly index
        hrs = pd.date_range(hist.index.min(), hist.index.max(), freq="h")

        # price: forward/backfill to eliminate gaps
        price_series = hist["price"].reindex(hrs).ffill().bfill()

        # sentiment: average per hour, missing => 0
        sent_hourly = (
            sent_df[sent_df["Coin"]==coin]
              .set_index("Timestamp")["Sentiment"]
              .resample("h").mean()
              .reindex(hrs, fill_value=0.0)
        )

        df = pd.DataFrame({
            "Timestamp": hrs,
            "Price (USD)": price_series,
            "Sentiment":  sent_hourly
        })

        # price trace
        fig = px.line(df, x="Timestamp", y="Price (USD)")
        fig.data[0].name = "Price"

        # overlay sentiment
        fig.add_scatter(
            x=df["Timestamp"],
            y=df["Sentiment"],
            mode="lines",
            name="Avg Sentiment",
            yaxis="y2"
        )

        fig.update_layout(
            title=f"{coin} — Price vs Sentiment (Last {HISTORY_DAYS} Days)",
            xaxis=dict(rangeslider=dict(visible=True)),
            yaxis=dict(title="Price (USD)"),
            yaxis2=dict(
                title="Avg Sentiment",
                overlaying="y",
                side="right"
            ),
            legend=dict(y=1.1, orientation="h")
        )
        st.plotly_chart(fig, use_container_width=True)

    # ─── 3) Next Hour Predictions ──────────────────────────────────────────
    with tabs[2]:
        st.header("Next Hour Predictions")
        now      = datetime.datetime.utcnow()
        cutoff24 = now - datetime.timedelta(hours=24)

        rows = []
        for c in COINS:
            curr    = current_prices.get(c, 0.0)
            entries = pred_log.get(c, [])
            latest  = entries[0] if entries else {}
            pred    = latest.get("predicted")

            # Δ %
            if pred is not None and curr:
                pct   = (pred - curr) / curr * 100
                arrow = "↑" if pct >= 0 else "↓"
                delta = f"{arrow}{abs(pct):.1f}%"
            else:
                delta = "N/A"

            # 24h accuracy
            recent = [
                e for e in entries
                if parser.isoparse(e["timestamp"]).replace(tzinfo=None) >= cutoff24
                   and e.get("accurate") is not None
            ]
            if recent:
                acc = sum(1 for e in recent if e["accurate"]) / len(recent) * 100
                acc_str = f"{acc:.0f}%"
            else:
                acc_str = "N/A"

            rows.append({
                "Coin":      c,
                "Current":   f"${curr:,.2f}",
                "Predicted": f"${pred:,.2f}" if pred is not None else "N/A",
                "Δ %":       delta,
                "24 h Acc":  acc_str
            })

        st.table(pd.DataFrame(rows))

if __name__ == "__main__":
    main()
