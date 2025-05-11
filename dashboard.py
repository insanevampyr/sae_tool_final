import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Crypto Sentiment Dashboard", layout="wide")

st.title("📊 Crypto Sentiment Dashboard")

# Load CSV data
df = pd.read_csv("sentiment_output.csv")

# Coin selection
coins = df["Coin"].unique()
selected_coin = st.selectbox("Choose a coin to view sentiment analysis:", coins)

# Filter data
filtered = df[df["Coin"] == selected_coin]

# Plot bar chart (average sentiment by source)
st.subheader(f"📈 Sentiment Chart for {selected_coin}")
fig, ax = plt.subplots(figsize=(8, 5))
avg_sentiment = filtered.groupby("Source")["Sentiment"].mean()
colors = ['green' if s > 0 else 'red' for s in avg_sentiment]
ax.bar(avg_sentiment.index, avg_sentiment.values, color=colors)
ax.set_title(f"Average Sentiment by Source for {selected_coin}")
ax.set_ylabel("Sentiment Score")
st.pyplot(fig)

# Show sentiment table
st.subheader(f"📋 Sentiment Entries for {selected_coin}")
st.dataframe(filtered[["Source", "Sentiment", "SuggestedAction", "Text", "Link"]].sort_values(by="Sentiment", ascending=False))
