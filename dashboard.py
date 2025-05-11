import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime
from send_telegram import send_telegram_message

st.set_page_config(page_title="Crypto Sentiment Dashboard", layout="wide")

st.title("📊 Crypto Sentiment Dashboard")
st.markdown("Get live sentiment analysis from Reddit and crypto news.")

csv_path = "sentiment_output.csv"
chart_path = "sentiment_chart.png"
json_path = "previous_actions.json"
history_path = "sentiment_history.csv"

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

# Sidebar summary
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

# Tabs for layout
tab1, tab2 = st.tabs(["📈 Current Sentiment", "📉 Trends"])

with tab1:
    if os.path.exists(chart_path):
        st.image(chart_path, caption="Sentiment by Coin and Source", use_container_width=True)

    coin_filter = st.selectbox("Select a coin to view details:", ["All"] + sorted(data["Coin"].unique()))
    filtered = data if coin_filter == "All" else data[data["Coin"] == coin_filter]

    expected_columns = ["Source", "Sentiment", "SuggestedAction", "Text", "Link"]
    available_columns = [col for col in expected_columns if col in filtered.columns]

    if available_columns:
        st.dataframe(filtered[available_columns].sort_values(by="Sentiment", ascending=False))
    else:
        st.warning("No matching columns available to display.")

with tab2:
    st.subheader("📊 Historical Sentiment Trends")
    if os.path.exists(history_path):
        history_df = pd.read_csv(history_path)
        history_df['Timestamp'] = pd.to_datetime(history_df['Timestamp'])
        last_year = datetime.utcnow().year - 1
        one_year_df = history_df[history_df['Timestamp'].dt.year >= last_year]

        for coin in sorted(one_year_df['Coin'].unique()):
            st.markdown(f"### {coin}")
            fig, ax = plt.subplots()
            for source in one_year_df['Source'].unique():
                subset = one_year_df[(one_year_df['Coin'] == coin) & (one_year_df['Source'] == source)]
                ax.plot(subset['Timestamp'], subset['Sentiment'], marker='o', label=source)
            ax.set_title(f"Sentiment Trend for {coin} (Past Year)")
            ax.set_ylabel("Sentiment Score")
            ax.axhline(0, color='gray', linestyle='--')
            ax.legend()
            st.pyplot(fig)
    else:
        st.warning("No historical sentiment data found. Run analyze.py regularly to build history.")
