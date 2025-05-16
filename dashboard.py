import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import json
import os
from datetime import datetime, timezone, timedelta
from sklearn.linear_model import LinearRegression

from send_telegram import send_telegram_message
from fetch_prices    import fetch_prices

# bring in your update_predictions() from analyze.py
from analyze import update_predictions

# — Setup Streamlit —
st.set_page_config(page_title="AlphaPulse | Sentiment Dashboard", layout="wide")
st.image("alpha_logo.jpg", use_container_width=True)
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("Live crypto sentiment analysis, historical trends, and ML forecasts.")

# — File paths —
csv_path      = "sentiment_output.csv"
history_file  = "sentiment_history.csv"
actions_path  = "previous_actions.json"
ml_log_path   = "prediction_log.json"

def load_data(path):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception as e:
            st.error(f"Failed to load {path}: {e}")
    return pd.DataFrame()

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}

def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

#
# 1) Load & pre-update your prediction_log.json
#
update_predictions()       # ← fill in any “actual” prices older than 1h
log     = load_json(ml_log_path)

#
# 2) Load your other data sources
#
raw     = load_data(csv_path)
history = load_data(history_file)
actions = load_json(actions_path)
prices  = fetch_prices()
now     = datetime.now(timezone.utc)

#
# 3) Sidebar: Sentiment summary & alerts
#
st.sidebar.header("📌 Sentiment Summary")
range_opts = ["Last 24 Hours","Last 7 Days","Last 30 Days"]
cutoffs = {
    "Last 24 Hours": now - timedelta(days=1),
    "Last 7 Days":   now - timedelta(days=7),
    "Last 30 Days":  now - timedelta(days=30),
}
summary_range  = st.sidebar.selectbox("Summary Window", range_opts, index=0)
cutoff_summary = cutoffs[summary_range]

if "Timestamp" in raw.columns:
    raw["Timestamp"] = pd.to_datetime(raw["Timestamp"], utc=True, errors="coerce")
else:
    st.sidebar.warning("⚠️ No 'Timestamp' in sentiment_output.csv")

raw.drop_duplicates(inplace=True)
recent = raw[raw["Timestamp"] >= cutoff_summary]
if recent.empty:
    st.sidebar.warning(f"No data in {summary_range}; showing all.")
    recent = raw

overall = recent.groupby("Coin")["Sentiment"].mean().round(3)
for coin, avg in overall.items():
    action = "📈 Buy" if avg > 0.2 else "📉 Sell" if avg < -0.2 else "🤝 Hold"
    st.sidebar.write(f"**{coin}**: {avg:.3f} → {action}")
    key = f"alert_{coin}"
    if st.sidebar.checkbox(f"🔔 Alert for {coin}", key=key):
        if actions.get(coin) != action:
            send_telegram_message(f"⚠️ **{coin} Action Changed**\nSentiment: {avg:.3f}\n→ {action}")
            actions[coin] = action
save_json(actions, actions_path)

#
# 4) Main: ML Price Predictions with actuals
#
st.markdown("### 🤖 ML Price Predictions")
if history.empty:
    st.info("No historical data for ML predictions.")
else:
    history["Timestamp"] = pd.to_datetime(history["Timestamp"], utc=True, errors="coerce")
    tolerance = 4
    st.markdown(f"_Accuracy tolerance: ±{tolerance}%_")

    for coin in sorted(history["Coin"].dropna().unique()):
        df = history[history["Coin"] == coin].sort_values("Timestamp")
        if len(df) < 6:
            continue

        # simple linear‐regression forecast
        X = np.arange(len(df)).reshape(-1,1)
        y = df["PriceUSD"].values.reshape(-1,1)
        model = LinearRegression().fit(X, y)
        pred  = float(model.predict([[len(df)]])[0][0])
        curr  = float(y[-1][0])
        diff_pct = (pred - curr) / curr * 100
        dir_arrow = "↑" if diff_pct>0 else "↓"
        future_t  = (now + timedelta(hours=1)).strftime("%H:%M UTC")

        # pull matching entry from log
        entries = log.get(coin, [])
        last    = entries[-1] if entries else {}
        actual  = last.get("actual")
        accurate= last.get("accurate")
        err_pct = last.get("diff_pct")

        # display panel
        bg = "#ccffcc" if accurate else "#ffcccc" if accurate is False else "#f1f1f1"
        verdict = ("✅ Accurate" if accurate
                   else "❌ Off"     if accurate is False
                   else "🕒 Pending")

        st.markdown(f"""
        <div style='background:{bg};padding:1rem;margin-bottom:0.5rem;border-radius:5px;'>
          <b>{coin}</b>: Pred ${pred:,.2f} ({dir_arrow}{abs(diff_pct):.2f}%) by {future_t}<br>
          Actual: {f"${actual:,.2f}" if actual else "_awaiting_"} — Error: {f"{err_pct:.2f}%" if err_pct is not None else "_n/a_"}<br>
          <b>Accuracy:</b> {verdict}
        </div>
        """, unsafe_allow_html=True)

#
# 5) Trends Over Time
#
st.markdown("### 📈 Trends Over Time")
if not history.empty:
    coin = st.selectbox("Select coin:", sorted(history["Coin"].dropna().unique()))
    df_c = history[history["Coin"] == coin]
    if not df_c.empty:
        fig, ax1 = plt.subplots(figsize=(10,5))
        loc = mdates.AutoDateLocator(minticks=3, maxticks=7)
        fmt = mdates.ConciseDateFormatter(loc)
        ax1.xaxis.set_major_locator(loc)
        ax1.xaxis.set_major_formatter(fmt)

        ax1.plot(df_c["Timestamp"], df_c["Sentiment"], "o-", label="Sentiment", color="#1f77b4")
        ax1.set_ylabel("Sentiment")

        ax2 = ax1.twinx()
        ax2.plot(df_c["Timestamp"], df_c["PriceUSD"], "--", label="Price (USD)", color="#2ca02c")
        ax2.set_ylabel("Price (USD)")

        plt.title(f"{coin} — Sentiment & Price")
        st.pyplot(fig)
    else:
        st.info("No data for that coin in this window.")

#
# 6) Raw sentiment table
#
st.subheader("📋 Sentiment Details")
if not raw.empty:
    flt = st.selectbox("Filter by coin:", ["All"] + sorted(raw["Coin"].unique()))
    df  = raw if flt=="All" else raw[raw["Coin"]==flt]
    st.dataframe(df.sort_values("Timestamp", ascending=False), use_container_width=True)
else:
    st.info("No raw sentiment data.")
