import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Set page config at the top
st.set_page_config(page_title="Crypto Sentiment Dashboard", layout="wide")

# Load sentiment data
st.title("📊 Crypto Sentiment Dashboard")

try:
    df = pd.read_csv("sentiment_output.csv")
except FileNotFoundError:
    st.error("Sentiment data not found. Run analyze.py first.")
    st.stop()

# Format timestamp
df["Timestamp"] = pd.to_datetime(df["Timestamp"])

# Sidebar filters
coins = df["Coin"].unique().tolist()
sources = df["Source"].unique().tolist()

st.sidebar.header("🔍 Filter Data")
selected_coin = st.sidebar.selectbox("Select Coin", ["All"] + coins)
selected_source = st.sidebar.selectbox("Select Source", ["All"] + sources)
sentiment_range = st.sidebar.slider("Sentiment Threshold", -1.0, 1.0, (-1.0, 1.0))

# Apply filters
filtered = df.copy()
if selected_coin != "All":
    filtered = filtered[filtered["Coin"] == selected_coin]
if selected_source != "All":
    filtered = filtered[filtered["Source"] == selected_source]
filtered = filtered[(filtered["Sentiment"] >= sentiment_range[0]) & (filtered["Sentiment"] <= sentiment_range[1])]

# Format SuggestedAction column
if "SuggestedAction" not in filtered.columns and "Action" in filtered.columns:
    filtered["SuggestedAction"] = filtered["Action"]

# Conditional formatting
def highlight_sentiment(val):
    if val > 0.2:
        return "color: green"
    elif val < -0.2:
        return "color: red"
    return ""

def bold_action(val):
    return "font-weight: bold"

# Display filtered data
st.subheader("📄 Filtered Sentiment Data")
st.dataframe(
    filtered[["Coin", "Source", "Sentiment", "SuggestedAction"]]
    .style.applymap(highlight_sentiment, subset=["Sentiment"])
    .applymap(bold_action, subset=["SuggestedAction"])
)

# Grouped sentiment chart
st.subheader("📈 Average Sentiment per Coin")
grouped = filtered.groupby("Coin")["Sentiment"].mean().reset_index()
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(grouped["Coin"], grouped["Sentiment"], color="skyblue")
ax.axhline(0, color="gray", linestyle="--")
ax.set_ylabel("Avg Sentiment")
ax.set_title("Average Sentiment per Coin")
plt.xticks(rotation=45)
st.pyplot(fig)

# Footer
st.markdown(f"---")
st.caption(f"Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
st.caption("Data sourced from Reddit and top crypto news feeds.")
