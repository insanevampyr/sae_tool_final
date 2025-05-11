import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime
from send_telegram import send_telegram_message

st.set_page_config(page_title="Crypto Sentiment Dashboard", layout="wide")

st.title("📊 Crypto Sentiment Dashboard")
st.markdown("Track real-time sentiment and price trends for your favorite cryptocurrencies.")

# --- File paths ---
csv_path = "sentiment_output.csv"
chart_path = "sentiment_chart.png"
json_path = "previous_actions.json"
history_file = "sentiment_history.csv"

# --- Load data ---
def load_data():
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    else:
        st.error("Sentiment output not found. Please run analyze.py first.")
        return pd.DataFrame()

def load_previous_actions():
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            return json.load(f)
    return {}

def save_previous_actions(data):
    with open(json_path, "w") as f:
        json.dump(data, f)

data = load_data()
previous_actions = load_previous_actions()

# --- Sidebar summary ---
st.sidebar.header("📌 Sentiment Summary")
overall_sentiments = data.groupby("Coin")["Sentiment"].mean()
summary_table = []

for coin, sentiment in overall_sentiments.items():
    action = "📈 Buy" if sentiment > 0.2 else "📉 Sell" if sentiment < -0.2 else "🤝 Hold"
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    st.sidebar.write(f"**{coin}**: {sentiment:.2f} → {action}")
    st.sidebar.caption(f"_Updated: {timestamp}_")

    summary_table.append({"Coin": coin, "Sentiment": sentiment, "Action": action, "Time": timestamp})

    toggle_key = f"alert_toggle_{coin}"
    if st.sidebar.checkbox(f"🔔 Alert for {coin}", key=toggle_key):
        last_action = previous_actions.get(coin)
        if last_action != action:
            msg = f"⚠️ **{coin} Action Changed**\nNew Avg Sentiment: {sentiment:.2f}\n**Suggested Action:** {action}"
            send_telegram_message(msg)
            previous_actions[coin] = action

save_previous_actions(previous_actions)

# --- Show sentiment bar chart ---
if os.path.exists(chart_path):
    st.image(chart_path, caption="Sentiment by Coin and Source", use_container_width=True)

# --- Coin filter ---
coin_filter = st.selectbox("Select a coin to view details:", ["All"] + sorted(data["Coin"].unique()))
filtered = data if coin_filter == "All" else data[data["Coin"] == coin_filter]

expected_columns = ["Source", "Sentiment", "SuggestedAction", "Text", "Link"]
available_columns = [col for col in expected_columns if col in filtered.columns]
if available_columns:
    st.dataframe(filtered[available_columns].sort_values(by="Sentiment", ascending=False))
else:
    st.warning("No matching columns available to display.")

# --- Trends tab ---
st.subheader("📈 Trends Over Time")
if os.path.exists(history_file):
    history = pd.read_csv(history_file)
    history["Timestamp"] = pd.to_datetime(history["Timestamp"])

    coin_options = sorted(history["Coin"].unique())
    selected_coin = st.selectbox("Trend for coin:", coin_options)

    coin_history = history[history["Coin"] == selected_coin]
    if not coin_history.empty:
        fig, ax1 = plt.subplots(figsize=(10, 5))
        ax1.plot(coin_history["Timestamp"], coin_history["Sentiment"], label="Sentiment", color="blue")
        ax1.set_ylabel("Sentiment", color="blue")
        ax1.tick_params(axis="y", labelcolor="blue")

        if "PriceUSD" in coin_history.columns:
            ax2 = ax1.twinx()
            ax2.plot(coin_history["Timestamp"], coin_history["PriceUSD"], color="green", linestyle="--", label="Price (USD)")
            ax2.set_ylabel("Price (USD)", color="green")
            ax2.tick_params(axis="y", labelcolor="green")

        ax1.set_title(f"Sentiment{' & Price' if 'PriceUSD' in coin_history.columns else ''} Trends for {selected_coin}")
        fig.autofmt_xdate()
        st.pyplot(fig)
    else:
        st.info("No trend data available for this coin yet.")
else:
    st.warning("sentiment_history.csv not found. Please run analyze.py to build history.")
