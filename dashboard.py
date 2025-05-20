import streamlit as st
import pandas as pd
import numpy as np
import joblib
import altair as alt
import json
import os

COINS = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]

# --- Utility Functions ---

def load_csv(path, date_cols=[], float_cols=[], str_cols=[]):
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()
        for c in date_cols:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], utc=True, errors='coerce')
        for c in float_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        for c in str_cols:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Could not load {path}: {e}")
        return pd.DataFrame()

def load_model():
    path = "price_predictor.pkl"
    if not os.path.exists(path):
        return None
    obj = joblib.load(path)
    # Some joblibs save (model, extra), just use model
    if isinstance(obj, tuple):
        return obj[0]
    return obj

def load_prediction_log():
    if not os.path.exists("prediction_log.json"):
        return {}
    with open("prediction_log.json") as f:
        return json.load(f)

# --- Load Data Upfront ---

sent_hist = load_csv(
    "sentiment_history.csv",
    date_cols=["Timestamp"],
    float_cols=["Sentiment"],
    str_cols=["Coin"]
)
sent_out = load_csv(
    "sentiment_output.csv",
    date_cols=["Timestamp"],
    float_cols=["Sentiment"],
    str_cols=["Coin"]
)
price_hist = load_csv(
    "btc_history.csv",
    date_cols=["Timestamp"],
    float_cols=["PriceUSD"],
    str_cols=["Coin"]
)

model = load_model()
pred_log = load_prediction_log()

# --- Streamlit Config ---

st.set_page_config("Crypto Dashboard", layout="wide")
st.title("📊 Crypto Sentiment & Price Dashboard")

tabs = st.tabs([
    "Sentiment Summary (24hr Avg)",
    "Trends Over Time",
    "Next Hour Predictions"
])

# --- Tab 1: Sentiment Summary (24hr Avg) ---

with tabs[0]:
    st.header("Sentiment Summary (Last 24h Avg per Coin)")
    if sent_hist.empty:
        st.warning("No sentiment_history.csv data found.")
    else:
        now = pd.Timestamp.utcnow()
        last24 = sent_hist[sent_hist["Timestamp"] >= now - pd.Timedelta(hours=24)]
        summary = (
            last24.groupby("Coin")["Sentiment"]
            .mean()
            .reindex(COINS)
            .reset_index()
            .rename(columns={"Sentiment": "24h Avg Sentiment"})
        )
        summary["24h Avg Sentiment"] = summary["24h Avg Sentiment"].round(4)
        st.dataframe(summary, hide_index=True, use_container_width=True)

# --- Tab 2: Trends Over Time ---

with tabs[1]:
    st.header("Trends Over Time")
    coin = st.selectbox("Select coin", COINS, key="trend_coin")
    s = sent_hist[sent_hist["Coin"] == coin].sort_values("Timestamp")
    p = price_hist[price_hist["Coin"] == coin].sort_values("Timestamp")
    # Merge by nearest timestamp within 1 hour, last 48h only
    if not s.empty and not p.empty:
        max_time = min(s["Timestamp"].max(), p["Timestamp"].max())
        recent_cut = max_time - pd.Timedelta(hours=48)
        s = s[s["Timestamp"] >= recent_cut]
        p = p[p["Timestamp"] >= recent_cut]
        merged = pd.merge_asof(
            p.set_index("Timestamp"),
            s.set_index("Timestamp"),
            left_index=True,
            right_index=True,
            direction='nearest',
            tolerance=pd.Timedelta('1h')
        ).reset_index()

        # Fix: check columns before dropna
        if "PriceUSD" in merged.columns and "Sentiment" in merged.columns:
            merged = merged.dropna(subset=["PriceUSD", "Sentiment"])
            # Normalize sentiment for graph overlay
            sent_min, sent_max = merged["Sentiment"].min(), merged["Sentiment"].max()
            price_min, price_max = merged["PriceUSD"].min(), merged["PriceUSD"].max()
            scale = (price_max - price_min) / (sent_max - sent_min) if sent_max != sent_min else 1
            merged["Sent_Scaled"] = price_min + (merged["Sentiment"] - sent_min) * scale

            base = alt.Chart(merged).encode(x="Timestamp:T")
            price_line = base.mark_line(y="PriceUSD:Q", color=alt.value("#0366d6")).properties(title=f"{coin} Price vs Sentiment (last 48h)")
            sent_line = base.mark_line(y="Sent_Scaled:Q", color=alt.value("orange")).encode(tooltip=["Sentiment:Q"])
            chart = price_line + sent_line
            st.altair_chart(chart, use_container_width=True)
            st.caption("Blue = Price (USD), Orange = Sentiment (overlayed & scaled to fit price range)")
        else:
            st.warning("No price or sentiment data available after merge for this coin and timeframe.")
    else:
        st.info("No data for this coin for the last 48h.")

# --- Tab 3: Next Hour Predictions ---

with tabs[2]:
    st.header("Next Hour Predictions")
    if (model is not None) and (not sent_out.empty):
        sents = []
        for c in COINS:
            row = sent_out[sent_out["Coin"] == c].sort_values("Timestamp")
            val = row.iloc[-1]["Sentiment"] if not row.empty else 0.0
            sents.append(val if not pd.isnull(val) else 0.0)
        preds = model.predict(np.array(sents).reshape(-1, 1))
        pred_df = pd.DataFrame({
            "Coin": COINS,
            "Latest Sentiment": np.round(sents, 4),
            "Predicted Next Price": np.round(preds, 2)
        })
        st.dataframe(pred_df, use_container_width=True, hide_index=True)
    else:
        st.warning("Prediction model or sentiment_output.csv not available.")

    st.markdown("----")
    st.subheader("Last Predictions Log")
    log_rows = []
    for coin in COINS:
        entries = pred_log.get(coin, [])
        if entries:
            entry = entries[-1]
            log_rows.append({
                "Coin": coin,
                "Timestamp": entry.get("timestamp"),
                "Predicted": entry.get("predicted"),
                "Actual": entry.get("actual"),
                "Diff %": entry.get("diff_pct"),
                "Accurate?": entry.get("accurate"),
            })
    if log_rows:
        st.dataframe(pd.DataFrame(log_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No recent prediction log found.")

# -- End of file --
