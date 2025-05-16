# dashboard.py
import os, json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone, timedelta
from send_telegram import send_telegram_message
from fetch_prices import fetch_prices

# --- Page config ---
st.set_page_config(page_title="AlphaPulse | Sentiment Dashboard", layout="wide")
st.image("alpha_logo.jpg", use_container_width=True)
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")
st.markdown("Live crypto sentiment analysis, historical trends, and ML forecasts.")

# --- Load helpers ---
def load_data(path):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.warning(f"⚠️ Could not parse '{path}'. Skipping.")
            return {}
    return {}

def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# --- Paths ---
csv_path = "sentiment_output.csv"
history_file = "sentiment_history.csv"
actions_path = "previous_actions.json"
ml_log_path = "prediction_log.json"

# --- Load data ---
raw = load_data(csv_path)
history = load_data(history_file)
actions = load_json(actions_path)
log = load_json(ml_log_path)
prices = fetch_prices()
now = datetime.now(timezone.utc)

# --- Sidebar: Sentiment Summary ---
st.sidebar.header("📌 Sentiment Summary")
ranges = ["Last 24 Hours","Last 7 Days","Last 30 Days"]
cutoffs = {
    ranges[0]: now - timedelta(days=1),
    ranges[1]: now - timedelta(days=7),
    ranges[2]: now - timedelta(days=30),
}
sel = st.sidebar.selectbox("Summary window:", ranges)
cut = cutoffs[sel]

if "Timestamp" in raw.columns:
    raw["Timestamp"] = pd.to_datetime(raw["Timestamp"], utc=True, errors="coerce")
else:
    st.sidebar.warning("⚠️ Missing 'Timestamp' in sentiment_output.csv")

recent = raw[raw["Timestamp"] >= cut] if not raw.empty else pd.DataFrame()
if recent.empty and not raw.empty:
    st.sidebar.warning(f"No data in {sel}; showing all.")
    recent = raw

actions_updated = False
for coin, avg in recent.groupby("Coin")["Sentiment"].mean().items() if not recent.empty else []:
    action = "📈 Buy" if avg>0.2 else "📉 Sell" if avg< -0.2 else "🤝 Hold"
    st.sidebar.write(f"**{coin}:** {avg:.3f} → {action}")
    key = f"alert_{coin}"
    if st.sidebar.checkbox(f"🔔 Alert for {coin}", key=key):
        if actions.get(coin) != action:
            send_telegram_message(f"⚠️ {coin} now **{action}** ({avg:.2f})")
            actions[coin] = action
            actions_updated = True
if actions_updated:
    save_json(actions, actions_path)

# --- ML Price Predictions ---
st.markdown("### 🤖 ML Price Predictions")
tolerance = 4
if log:
    st.markdown(f"_Accuracy tolerance: ±{tolerance}%_")
    for coin, entries in log.items():
        entry = entries[-1]
        pred = entry.get("predicted")
        actual = entry.get("actual")
        err_pct = entry.get("diff_pct", 0)
        acc = entry.get("accurate")
        ts = entry.get("timestamp", "").split("+")[0].replace("T"," ")
        icon = "✅" if acc else ("❌" if acc is False else "🕒")
        st.markdown(f"""
<div style='padding:1rem; margin-bottom:1rem; border-radius:8px; background:#f9f9f9;'>
  <b>{coin}</b>: Pred ${pred:,.2f} ({err_pct:+.2f}%) at {ts} UTC<br>
  <b>Actual:</b> {'$'+format(actual,',.2f') if actual else '_awaiting_'} — Error: {err_pct:+.2f}%<br>
  <b>Accuracy:</b> {icon}
</div>
""", unsafe_allow_html=True)
else:
    st.info("No ML prediction log found.")

# --- Trends Over Time ---
st.markdown("### 📈 Trends Over Time")
if not history.empty:
    history["Timestamp"] = pd.to_datetime(history["Timestamp"], utc=True, errors="coerce")
    coin = st.selectbox("Select coin:", sorted(history["Coin"].unique()))
    dfc = history[history["Coin"] == coin]
    if not dfc.empty:
        fig, ax1 = plt.subplots(figsize=(10,5))
        ax1.plot(dfc["Timestamp"], dfc["Sentiment"], marker="o", label="Sentiment")
        ax1.set_ylabel("Sentiment")
        ax2 = ax1.twinx()
        if "PriceUSD" in dfc.columns:
            ax2.plot(dfc["Timestamp"], dfc["PriceUSD"], linestyle="--", label="Price (USD)")
            ax2.set_ylabel("Price (USD)")
        ax1.xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
        plt.title(f"{coin} — Sentiment & Price Over Time")
        st.pyplot(fig)
    else:
        st.info("No history for this coin.")
else:
    st.warning("No historical data available.")

# --- Sentiment Details Table ---
st.subheader("📋 Sentiment Details")
if not raw.empty:
    df_clean = raw.drop_duplicates(subset=["Timestamp","Coin","Source","Text"], keep="last")
    cols = ["Coin","Sentiment","Action","Text","Source","Link","Timestamp"]
    df_display = df_clean[[c for c in cols if c in df_clean.columns]]
    st.dataframe(df_display.sort_values("Timestamp", ascending=False), use_container_width=True)
else:
    st.info("No sentiment data available.")
