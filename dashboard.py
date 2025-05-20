import streamlit as st
import pandas as pd
import numpy as np
import joblib
import altair as alt
import json
import os

COINS = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]

# === Loaders ===
@st.cache_data
def load_sentiment_history():
    df = pd.read_csv("sentiment_history.csv")
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    df = df[df["Timestamp"].notnull()]
    return df

@st.cache_data
def load_sentiment_output():
    df = pd.read_csv("sentiment_output.csv")
    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
        df = df[df["Timestamp"].notnull()]
    return df

@st.cache_data
def load_price_history():
    df = pd.read_csv("btc_history.csv")
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    df = df[df["Timestamp"].notnull()]
    return df

def load_model():
    model_path = "price_predictor.pkl"
    if os.path.exists(model_path):
        model = joblib.load(model_path)
        return model, COINS
    return None, None

def load_prediction_log():
    if os.path.exists("prediction_log.json"):
        with open("prediction_log.json", "r") as f:
            return json.load(f)
    return {}

# === Utility ===
def safe_float(x):
    try:
        return float(x)
    except:
        return np.nan

def get_next_hour_predictions(df):
    # Get latest sentiment for each coin
    preds = []
    for coin in COINS:
        coin_df = df[df["Coin"] == coin]
        if not coin_df.empty:
            val = coin_df.sort_values("Timestamp").iloc[-1]["Sentiment"]
            preds.append(safe_float(val))
        else:
            preds.append(0.0)
    return preds

# === Streamlit UI ===
st.set_page_config("Crypto Dashboard", layout="wide")
st.title("📈 Crypto Sentiment & Price Dashboard")

tabs = st.tabs([
    "Sentiment Summary (24hr Avg)", 
    "Trends Over Time", 
    "Next Hour Predictions"
])

# --- Sentiment Summary Tab ---
with tabs[0]:
    st.subheader("Sentiment Summary (Last 24h Average Per Coin)")
    sentiment = load_sentiment_history()
    now = pd.Timestamp.utcnow().tz_localize("UTC")
    cutoff = now - pd.Timedelta("24h")
    last24 = sentiment[sentiment["Timestamp"] >= cutoff]
    avg = (
        last24[last24["Sentiment"].apply(lambda x: isinstance(x, (int, float, np.number)) or str(x).replace('.', '', 1).isdigit())]
        .groupby("Coin")["Sentiment"]
        .mean()
        .reindex(COINS)
    )
    st.dataframe(
        pd.DataFrame({
            "Coin": COINS,
            "24h Avg Sentiment": np.round(avg.values, 4)
        }),
        use_container_width=True
    )

# --- Trends Over Time Tab ---
with tabs[1]:
    st.subheader("Trends Over Time")
    # Show a focused, zoomed-in chart
    sentiment = load_sentiment_history()
    price_hist = load_price_history()
    coin = st.selectbox("Coin", COINS, key="trend_coin")

    coin_sent = sentiment[sentiment["Coin"] == coin]
    coin_sent = coin_sent[coin_sent["Sentiment"].apply(lambda x: isinstance(x, (int, float, np.number)) or str(x).replace('.', '', 1).isdigit())]
    coin_sent["Sentiment"] = coin_sent["Sentiment"].astype(float)
    coin_sent = coin_sent.set_index("Timestamp").sort_index()

    coin_price = price_hist[price_hist["Coin"] == coin]
    coin_price = coin_price.set_index("Timestamp").sort_index()

    if not coin_sent.empty and not coin_price.empty:
        # Merge on nearest timestamp, forward-fill
        merged = pd.merge_asof(
            coin_price, 
            coin_sent, 
            left_index=True, right_index=True, 
            direction='nearest', 
            tolerance=pd.Timedelta('1H'),
            suffixes=("_price", "_sentiment")
        )
        # Drop rows with missing sentiment after merge
        merged = merged[merged["Sentiment"].notnull()]
        merged = merged.last("48h")  # zoom into the last 48h

        base = alt.Chart(merged.reset_index()).encode(
            x=alt.X("Timestamp:T", axis=alt.Axis(title="Time"))
        )
        price_line = base.mark_line().encode(
            y=alt.Y("PriceUSD:Q", axis=alt.Axis(title="Price (USD)"), scale=alt.Scale(zero=False)),
            color=alt.value("#007bff"),
            tooltip=["Timestamp:T", "PriceUSD:Q"]
        ).interactive()
        sent_line = base.mark_line(strokeDash=[5,5], color="orange").encode(
            y=alt.Y("Sentiment:Q", axis=alt.Axis(title="Sentiment")),
            tooltip=["Timestamp:T", "Sentiment:Q"]
        ).interactive()

        st.altair_chart(price_line + sent_line, use_container_width=True)
    else:
        st.warning("No sufficient data for selected coin.")

# --- Next Hour Predictions Tab ---
with tabs[2]:
    st.subheader("Next Hour Price Predictions (ML Model)")
    model, coins = load_model()
    if model is not None:
        curr_df = load_sentiment_output()
        sents = get_next_hour_predictions(curr_df)
        sents_clean = [x if not np.isnan(x) else 0.0 for x in sents]
        sents_np = np.array(sents_clean).reshape(-1, 1)
        preds = model.predict(sents_np)
        pred_df = pd.DataFrame({
            "Coin": COINS,
            "Latest Sentiment": np.round(sents_clean, 4),
            "Predicted Next Price": np.round(preds, 3)
        })
        st.dataframe(pred_df, use_container_width=True)
    else:
        st.warning("Prediction model not available. Run `train_price_predictor.py` to train.")

    # Show last predictions from log
    st.markdown("---")
    st.markdown("#### Last Predictions Log")
    pred_log = load_prediction_log()
    pred_rows = []
    for coin in COINS:
        if coin in pred_log and len(pred_log[coin]) > 0:
            entry = pred_log[coin][-1]
            pred_rows.append({
                "Coin": coin,
                "Timestamp": entry.get("timestamp"),
                "Predicted": entry.get("predicted"),
                "Actual": entry.get("actual", "N/A"),
                "Diff %": entry.get("diff_pct", "N/A"),
                "Accurate?": entry.get("accurate", "N/A"),
            })
    if pred_rows:
        st.dataframe(pd.DataFrame(pred_rows), use_container_width=True)
    else:
        st.info("No predictions logged yet.")

# === End ===
