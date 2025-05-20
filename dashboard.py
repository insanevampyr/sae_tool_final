import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
import altair as alt

# --- Config ---
st.set_page_config(page_title="AlphaPulse: Crypto Sentiment Pro", layout="centered")
LOGO_PATH = "alpha_logo.jpg"
COINS = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]

# --- Load Logo ---
if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=200)
st.markdown("<h1 style='text-align: center;'>AlphaPulse: Crypto Sentiment Pro</h1>", unsafe_allow_html=True)

# --- Load Data ---
@st.cache_data(ttl=600)
def load_sentiment_data():
    sh = pd.read_csv("sentiment_history.csv")
    so = pd.read_csv("sentiment_output.csv")
    for df in [sh, so]:
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return sh, so

@st.cache_data(ttl=600)
def load_prediction_log():
    with open("prediction_log.json") as f:
        pred_log = json.load(f)
    # Flatten structure
    flat = []
    for coin, entries in pred_log.items():
        for entry in entries:
            flat.append({
                "Coin": coin,
                "Timestamp": pd.to_datetime(entry["timestamp"]),
                "Predicted": entry["predicted"],
                "Actual": entry["actual"],
                "DiffPct": entry.get("diff_pct", 0)
            })
    return pd.DataFrame(flat)

@st.cache_data(ttl=600)
def load_latest_prices():
    for fname in ["latest_prices.csv", "btc_history.csv"]:
        if os.path.exists(fname):
            df = pd.read_csv(fname)
            if 'Coin' in df.columns and 'PriceUSD' in df.columns:
                return df.set_index("Coin")["PriceUSD"].to_dict()
    return {}

sent_hist, sent_out = load_sentiment_data()
pred_log = load_prediction_log()
latest_prices = load_latest_prices()

# --- Main Tabs ---
tab1, tab2, tab3 = st.tabs(["Sentiment Summary", "Trends Over Time", "Next Hour Prediction"])

# ----- TAB 1: Sentiment Summary -----
with tab1:
    st.subheader("24h Sentiment Average (per coin)")
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=24)
    df = sent_hist[sent_hist["Timestamp"] >= cutoff]

    table = []
    for coin in COINS:
        last_sent = df[df["Coin"] == coin].sort_values("Timestamp")
        if len(last_sent) < 2:
            continue
        avg24 = last_sent.tail(24)["Sentiment"].mean()
        change = avg24 - last_sent.head(1)["Sentiment"].iloc[0]
        color = "green" if change >= 0 else "red"
        table.append((coin, f"{avg24:.3f}", f":{color}[{change:+.3f}]"))
    st.table(pd.DataFrame(table, columns=["Coin", "24h Avg Sentiment", "Change"]))

# ----- TAB 2: Trends Over Time -----
with tab2:
    st.subheader("Price vs. Sentiment Trends")
    selected_coin = st.selectbox("Select coin:", COINS)
    coin_df = sent_hist[sent_hist["Coin"] == selected_coin].sort_values("Timestamp")
    window = 48  # show last 48 records/hours
    if len(coin_df) > window:
        coin_df = coin_df.tail(window)
    if not coin_df.empty:
        base = alt.Chart(coin_df).encode(x='Timestamp:T')
        price = base.mark_line(strokeWidth=2, color='blue').encode(y=alt.Y('PriceUSD:Q', axis=alt.Axis(title='Price (USD)')))
        sent = base.mark_line(strokeWidth=2, color='orange').encode(
            y=alt.Y('Sentiment:Q', axis=alt.Axis(title='Sentiment', titleColor='orange'))
        )
        chart = alt.layer(price, sent).resolve_scale(y='independent').interactive()
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Not enough data to display this chart.")

# ----- TAB 3: Next Hour Prediction -----
with tab3:
    st.subheader("Next Hour Predictions")
    # Get last entry for each coin from sentiment_history
    last_rows = sent_hist.sort_values("Timestamp").groupby("Coin").tail(1)
    price_now = {row["Coin"]: row["PriceUSD"] for _, row in last_rows.iterrows()}
    # Fallback if price missing
    for coin in COINS:
        if coin not in price_now and coin in latest_prices:
            price_now[coin] = latest_prices[coin]
    # Predicted price
    preds = {}
    pct_changes = {}
    for coin in COINS:
        # Find latest prediction for each coin
        pred_row = pred_log[pred_log["Coin"] == coin].sort_values("Timestamp").tail(1)
        if not pred_row.empty:
            pred_price = pred_row["Predicted"].iloc[0]
            preds[coin] = pred_price
            # Calc % change
            curr = price_now.get(coin, pred_price)
            pct = ((pred_price - curr) / curr) * 100 if curr else 0
            pct_changes[coin] = pct
        else:
            preds[coin] = "N/A"
            pct_changes[coin] = "N/A"
    # Calculate prediction accuracy for last 24h
    accs = {}
    for coin in COINS:
        coin_preds = pred_log[(pred_log["Coin"] == coin) & (pred_log["Timestamp"] >= now - timedelta(hours=24))]
        if not coin_preds.empty:
            diffs = np.abs((coin_preds["Predicted"] - coin_preds["Actual"]) / coin_preds["Actual"])
            acc = (1 - diffs.mean()) * 100
            accs[coin] = f"{acc:.1f}%"
        else:
            accs[coin] = "N/A"
    # Show Table
    rows = []
    for coin in COINS:
        curr = price_now.get(coin, "N/A")
        pred = preds.get(coin, "N/A")
        pct = pct_changes.get(coin, 0)
        color = "green" if isinstance(pct, float) and pct > 0 else "red"
        pct_display = f":{color}[{pct:+.2f}%]" if isinstance(pct, float) else "N/A"
        rows.append([coin, curr, pred, pct_display, accs[coin]])
    st.table(pd.DataFrame(rows, columns=["Coin", "Now", "Next Hour", "% Change", "24h Accuracy"]))
