# dashboard.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# This MUST be the first Streamlit command
st.set_page_config(page_title="Crypto Sentiment Dashboard", layout="wide")

# Load the CSV data
@st.cache_data
def load_data():
    return pd.read_csv("sentiment_output.csv")

df = load_data()

st.title("📊 Crypto Sentiment Dashboard")

# Show latest run date
if "Timestamp" in df.columns:
    latest = df["Timestamp"].max()
    st.caption(f"Latest Sentiment Snapshot: {latest}")

# Show legend
st.markdown("### Legend")
st.markdown("""
- **Sentiment Score:** Ranges from -1 (very negative) to +1 (very positive)
- **Suggested Action:**
  - 🔴 < -0.3 = Consider caution / exit
  - 🟡 -0.3 to 0.3 = Hold / Observe
  - 🟢 > 0.3 = Consider buying / optimism
""")

# Filter by Coin
coins = df["Coin"].unique()
selected_coin = st.selectbox("🔍 Choose a coin to analyze:", coins)

filtered = df[df["Coin"] == selected_coin]

# Display table
st.markdown("### Data Table")
st.dataframe(filtered[["Source", "Sentiment", "Action"]])

# Sentiment chart
st.markdown("### Sentiment Chart")

fig, ax = plt.subplots()
colors = filtered["Sentiment"].apply(lambda x: "green" if x > 0.3 else ("red" if x < -0.3 else "orange"))
ax.bar(filtered["Source"], filtered["Sentiment"], color=colors)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_ylabel("Sentiment Score")
ax.set_title(f"Sentiment Overview for {selected_coin}")
plt.xticks(rotation=30)
st.pyplot(fig)
