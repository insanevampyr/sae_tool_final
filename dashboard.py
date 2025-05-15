# dashboard.py
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
from fetch_prices import fetch_prices

st.set_page_config(page_title="AlphaPulse | Sentiment Dashboard", layout="wide")
st.image("alpha_logo.jpg", use_container_width=True)
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("Live crypto sentiment analysis, historical trends, and ML forecasts.")

csv_path      = "sentiment_output.csv"
history_file  = "sentiment_history.csv"
json_path     = "previous_actions.json"
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
        except:
            return {}
    return {}

def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

raw     = load_data(csv_path)
history = load_data(history_file)
actions = load_json(json_path)
log     = load_json(ml_log_path)
prices  = fetch_prices()
now     = datetime.now(timezone.utc)

# Sidebar Summary
st.sidebar.header("📌 Sentiment Summary")
range_opts = ["Last 24 Hours", "Last 7 Days", "Last 30 Days"]
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

if not recent.empty:
    overall = recent.groupby("Coin")["Sentiment"].mean()
    for coin, avg in overall.items():
        action = "📈 Buy" if avg > 0.2 else "📉 Sell" if avg < -0.2 else "🤝 Hold"
        st.sidebar.write(f"**{coin}**: {avg:.2f} → {action}")
        if st.sidebar.checkbox(f"🔔 Alert for {coin}", key=coin):
            if actions.get(coin) != action:
                msg = f"⚠️ **{coin} Action Changed**\nSentiment: {avg:.2f}\nSuggested: {action}"
                send_telegram_message(msg)
                actions[coin] = action
    save_json(actions, json_path)

# ML Predictions
st.markdown("### 🤖 ML Price Predictions")

if not history.empty:
    history.rename(columns=str.strip, inplace=True)
    history["Timestamp"] = pd.to_datetime(history["Timestamp"], utc=True, errors="coerce")
    history.drop_duplicates(inplace=True)

    tolerance = 4
    st.markdown(f"_Accuracy tolerance: ±{tolerance}%_")

    for coin in sorted(history["Coin"].dropna().unique()):
        df = history[history["Coin"] == coin].sort_values("Timestamp")
        if len(df) < 10:
            continue

        X = np.arange(len(df)).reshape(-1, 1)
        y = df["PriceUSD"].values.reshape(-1, 1)
        model = LinearRegression().fit(X, y)
        prediction = model.predict([[len(df)]])[0][0]
        current    = y[-1][0]
        diff_pct   = ((prediction - current) / current) * 100
        direction  = "↑" if diff_pct > 0 else "↓"
        color      = "green" if abs(diff_pct) >= tolerance else "gray"
        future_str = (now + timedelta(hours=1)).strftime("%H:%M UTC")

        # Accuracy
        last_known = df.iloc[-1]
        next_df    = df[df["Timestamp"] > last_known["Timestamp"]]
        actual     = next_df["PriceUSD"].values[0] if not next_df.empty else None

        was_correct = None
        if actual:
            err = abs((prediction - actual) / actual) * 100
            was_correct = err <= tolerance

        # Avoid malformed or duplicate log
        log.setdefault(coin, [])
        if not isinstance(log[coin], list):
            log[coin] = []

        last_log = log[coin][-1] if log[coin] else None
        if not last_log or last_log["timestamp"][:13] != now.isoformat()[:13]:
            log[coin].append({
                "timestamp": now.isoformat(),
                "predicted": round(prediction, 2),
                "actual": round(actual, 2) if actual else None,
                "diff_pct": round(diff_pct, 2),
                "accurate": was_correct
            })

            # Send Telegram alert if major movement
            if abs(diff_pct) >= tolerance:
                msg = f"🔮 ML Alert: {coin} → ${prediction:,.2f} ({diff_pct:+.2f}%) by {future_str}"
                send_telegram_message(msg)

        recent_correct = [x for x in log[coin][-24:] if x.get("accurate") is True]
        acc_24h = len(recent_correct)
        verdict = "✅ Accurate" if was_correct else "❌ Off" if was_correct is False else "🕒 Pending"
        bg = "#ccffcc" if was_correct else "#ffcccc" if was_correct is False else "#f1f1f1"
        font_color = "#222" if was_correct is None else "#000"

        st.markdown(f"""
        <div style='
            background-color:{bg};
            color:{font_color};
            padding:1rem;
            margin-bottom:0.5rem;
            border-radius:5px;
            font-size:16px;
        '>
            <b>{coin}</b>: ${prediction:,.2f} {direction} ({diff_pct:+.2f}%) by {future_str}<br>
            <b>Accuracy:</b> {verdict} — <b>{acc_24h}</b> correct in last 24h
        </div>
        """, unsafe_allow_html=True)

    save_json(log, ml_log_path)
else:
    st.info("No historical data available for ML predictions.")

# Trends
st.markdown("### 📈 Trends Over Time")
if not history.empty:
    coin = st.selectbox("Select coin:", sorted(history["Coin"].dropna().unique()))
    df_c = history[history["Coin"] == coin]

    if not df_c.empty:
        fig, ax1 = plt.subplots(figsize=(10, 5))
        locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
        ax1.xaxis.set_major_locator(locator)
        ax1.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax1.plot(df_c["Timestamp"], df_c["Sentiment"], marker="o", color="#1f77b4")
        ax1.set_ylabel("Sentiment", color="#1f77b4")

        ax2 = ax1.twinx()
        ax2.plot(df_c["Timestamp"], df_c["PriceUSD"], linestyle="--", color="#2ca02c")
        ax2.set_ylabel("Price (USD)", color="#2ca02c")

        plt.title(f"{coin} — Sentiment & Price Over Time")
        st.pyplot(fig)
    else:
        st.info("No trend data available.")
else:
    st.warning("📉 No historical data loaded.")

# Table
st.subheader("📋 Sentiment Details")
if not raw.empty:
    flt = st.selectbox("Filter by coin:", ["All"] + sorted(raw["Coin"].unique()))
    view = raw if flt == "All" else raw[raw["Coin"] == flt]
    key_cols = ["Timestamp", "Coin", "Source", "Sentiment", "Text", "Link"]
    view = view.drop_duplicates(subset=key_cols, keep="last")

    ordered = ["Coin", "Sentiment", "Action", "Text", "Source", "Link", "Timestamp"]
    display_cols = [c for c in ordered if c in view.columns]

    st.dataframe(view[display_cols].sort_values("Timestamp", ascending=False), use_container_width=True)
else:
    st.info("No sentiment data available.")
