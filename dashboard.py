import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="Crypto Sentiment Dashboard", layout="wide")
st.title("📊 Crypto Sentiment Dashboard")

# Load CSV
try:
    df = pd.read_csv("sentiment_output.csv")
except FileNotFoundError:
    st.error("❌ sentiment_output.csv not found!")
    st.stop()

# Ensure required columns exist
required_cols = ["Coin", "Source", "Sentiment"]
if not all(col in df.columns for col in required_cols):
    st.error("❌ Required columns missing from sentiment_output.csv")
    st.write("Expected columns:", required_cols)
    st.write("Found columns:", df.columns.tolist())
    st.stop()

# Sidebar summary by coin
st.sidebar.title("📌 Summary Overview")
summary = df.groupby("Coin")["Sentiment"].mean().reset_index()
summary["SuggestedAction"] = summary["Sentiment"].apply(
    lambda s: "📈 Buy" if s > 0.2 else ("📉 Sell" if s < -0.2 else "🤝 Hold")
)

now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
for _, row in summary.iterrows():
    st.sidebar.markdown(
        f"**{row['Coin']}**\n- Sentiment: `{row['Sentiment']:.2f}`\n- Action: `{row['SuggestedAction']}`"
    )
st.sidebar.caption(f"Last updated: {now}")

# Coin selection
coins = df["Coin"].unique()
selected_coin = st.selectbox("Choose a coin:", coins)

# Filter
filtered = df[df["Coin"] == selected_coin]

# Chart
st.subheader(f"📈 Sentiment Chart for {selected_coin}")
fig, ax = plt.subplots(figsize=(8, 5))
avg_sent = filtered.groupby("Source")["Sentiment"].mean()
colors = ['green' if x > 0 else 'red' for x in avg_sent]
ax.bar(avg_sent.index, avg_sent.values, color=colors)
ax.set_title(f"Average Sentiment by Source")
ax.set_ylabel("Sentiment Score")
st.pyplot(fig)

# Table
st.subheader(f"📋 Detailed Entries for {selected_coin}")
optional_cols = ["SuggestedAction", "Text", "Link"]
columns_to_show = ["Source", "Sentiment"] + [col for col in optional_cols if col in filtered.columns]
st.dataframe(filtered[columns_to_show].sort_values(by="Sentiment", ascending=False))
