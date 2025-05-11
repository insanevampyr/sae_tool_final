import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime
from send_telegram import send_telegram_message

st.set_page_config(page_title="Crypto Sentiment Dashboard", layout="wide")

st.title("📊 Crypto Sentiment Dashboard")

# Load sentiment data
csv_file = "sentiment_output.csv"
if not os.path.exists(csv_file):
    st.error("Sentiment data not found. Please run analyze.py first.")
    st.stop()

sentiment_data = pd.read_csv(csv_file)

# --- Sidebar: Coin sentiment summary with alerts toggle ---
st.sidebar.header("📌 Summary")

# Initialize session state to remember toggle value
if "telegram_alerts_enabled" not in st.session_state:
    st.session_state.telegram_alerts_enabled = True

st.sidebar.checkbox("Enable Telegram alerts for action changes", 
                    value=st.session_state.telegram_alerts_enabled,
                    key="telegram_alerts_enabled")

summary = sentiment_data.groupby("Coin")["Sentiment"].mean().reset_index()
summary["SuggestedAction"] = summary["Sentiment"].apply(lambda x: 
    "📈 Buy" if x > 0.2 else "📉 Sell" if x < -0.2 else "🤝 Hold")

now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
st.sidebar.markdown(f"**Last updated:** {now}")

# Track previous actions for alert comparison
previous_actions_file = "previous_actions.json"
previous_actions = {}
if os.path.exists(previous_actions_file):
    with open(previous_actions_file, "r") as f:
        previous_actions = json.load(f)

# Show and check for changes
for _, row in summary.iterrows():
    coin = row["Coin"]
    sentiment = round(row["Sentiment"], 2)
    action = row["SuggestedAction"]
    st.sidebar.write(f"**{coin}**: {sentiment} → {action}")

    # Alert if action changed
    prev = previous_actions.get(coin)
    if prev is None or prev["action"] != action:
        if st.session_state.telegram_alerts_enabled:
            msg = (
                f"🔔 *Suggested Action Changed for {coin}*\n"
                f"Previous: {prev['action'] if prev else 'N/A'}\n"
                f"Now: {action}\n"
                f"Sentiment Score: {sentiment}"
            )
            send_telegram_message(msg)

        previous_actions[coin] = {"action": action, "sentiment": sentiment}

# Save updated actions
with open(previous_actions_file, "w") as f:
    json.dump(previous_actions, f)

# --- Main Table ---
st.markdown("### 🔍 Sentiment Entries")
selected_coin = st.selectbox("Select a coin to filter", ["All"] + list(summary["Coin"]))
filtered = sentiment_data[sentiment_data["Coin"] == selected_coin] if selected_coin != "All" else sentiment_data
st.dataframe(filtered[["Source", "Sentiment", "Action", "Text", "Link"]].sort_values(by="Sentiment", ascending=False))

# --- Chart ---
st.markdown("### 📈 Average Sentiment by Coin and Source")
fig, ax = plt.subplots(figsize=(10, 6))
plot_data = sentiment_data.groupby(["Coin", "Source"])["Sentiment"].mean().unstack()
plot_data.plot(kind="bar", ax=ax)
ax.set_ylabel("Sentiment Score")
ax.set_title("Sentiment Breakdown by Coin and Source")
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
st.pyplot(fig)
