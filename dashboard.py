import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime
from send_telegram import send_telegram_message

st.set_page_config(page_title="Crypto Sentiment Dashboard", layout="wide")

st.title("📊 Crypto Sentiment Dashboard")
st.markdown("Get live sentiment and price trends from Reddit, crypto news, and price feeds.")

# Load latest sentiment snapshot
data = pd.read_csv("sentiment_output.csv") if os.path.exists("sentiment_output.csv") else pd.DataFrame()
chart_path = "sentiment_chart.png"
json_path = "previous_actions.json"
history_file = "sentiment_history.csv"

# Load previous Telegram state
if os.path.exists(json_path):
    with open(json_path, "r") as f:
        previous_actions = json.load(f)
else:
    previous_actions = {}

def save_previous_actions(data):
    with open(json_path, "w") as f:
        json.dump(data, f)

# Sidebar summary
st.sidebar.header("📌 Sentiment Summary")
if not data.empty:
    overall_sentiments = data.groupby("Coin")["Sentiment"].mean()
    for coin, sentiment in overall_sentiments.items():
        action = "📈 Buy" if sentiment > 0.2 else "📉 Sell" if sentiment < -0.2 else "🤝 Hold"
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        st.sidebar.write(f"**{coin}**: {sentiment:.2f} → {action}")
        st.sidebar.caption(f"_Updated: {timestamp}_")

        toggle_key = f"alert_toggle_{coin}"
        if st.sidebar.checkbox(f"🔔 Alert for {coin}", key=toggle_key):
            last_action = previous_actions.get(coin)
            if last_action != action:
                msg = f"⚠️ **{coin} Action Changed**\nNew Avg Sentiment: {sentiment:.2f}\n**Suggested Action:** {action}"
                send_telegram_message(msg)
                previous_actions[coin] = action

save_previous_actions(previous_actions)

# Show bar chart
if os.path.exists(chart_path):
    st.image(chart_path, caption="Sentiment by Coin and Source", use_container_width=True)

# Select coin filter
coin_filter = st.selectbox("Select a coin to view details:", ["All"] + sorted(data["Coin"].unique())) if not data.empty else "All"
filtered = data if coin_filter == "All" else data[data["Coin"] == coin_filter]

if not filtered.empty:
    cols = [col for col in ["Source", "Sentiment", "SuggestedAction", "Text", "Link"] if col in filtered.columns]
    st.dataframe(filtered[cols].sort_values(by="Sentiment", ascending=False))

# Trends tab
st.header("📈 Historical Sentiment & Price Trends")
if os.path.exists(history_file):
    history = pd.read_csv(history_file)
    selected_coin = st.selectbox("Choose coin for trends:", sorted(history["Coin"].unique()))
    coin_history = history[history["Coin"] == selected_coin]
    
    fig, ax1 = plt.subplots(figsize=(12, 5))

    ax1.plot(coin_history["Timestamp"], coin_history["Sentiment"], color="blue", label="Sentiment")
    ax1.set_ylabel("Sentiment", color="blue")
    ax1.tick_params(axis='y', labelcolor='blue')
    ax1.set_xticks(coin_history["Timestamp"][::max(len(coin_history)//10, 1)])
    ax1.set_xticklabels(coin_history["Timestamp"][::max(len(coin_history)//10, 1)], rotation=45, ha="right")

    ax2 = ax1.twinx()
    ax2.plot(coin_history["Timestamp"], coin_history["PriceUSD"], color="green", linestyle="--", label="Price (USD)")
    ax2.set_ylabel("Price (USD)", color="green")
    ax2.tick_params(axis='y', labelcolor='green')

    fig.tight_layout()
    st.pyplot(fig)
else:
    st.info("Run `analyze.py` at least once to generate sentiment history.")
