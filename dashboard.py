import streamlit as st
import pandas as pd
import altair as alt
import os

DATA_FILE = "sentiment_output.csv"
HIST_FILE = "sentiment_history.csv"

st.set_page_config(page_title="Crypto Sentiment Dashboard", layout="wide")
st.title("Crypto Sentiment Dashboard")

# --- Data Loading ---
def load_data(path):
    if os.path.exists(path):
        df = pd.read_csv(path)
        # Standardize columns
        df.columns = [c.strip() for c in df.columns]
        # Force correct types for Timestamp
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
        return df
    else:
        st.warning(f"File not found: {path}")
        return pd.DataFrame()

df = load_data(DATA_FILE)
hist = load_data(HIST_FILE)

if df.empty:
    st.error("No data loaded! Check that sentiment_output.csv exists and is not empty.")
    st.stop()

required_cols = {"Coin", "Timestamp", "Sentiment", "PriceUSD", "SuggestedAction"}
if not required_cols.issubset(set(df.columns)):
    st.error(f"Missing columns in data: {required_cols - set(df.columns)}")
    st.dataframe(df)
    st.stop()

# --- Show Latest for Each Coin ---
st.subheader("Latest Sentiment and Price per Coin")
latest = df.sort_values("Timestamp").groupby("Coin").tail(1).sort_values("Coin")
st.dataframe(latest[["Coin", "Timestamp", "Sentiment", "PriceUSD", "SuggestedAction"]].reset_index(drop=True))

# --- All Recent Data Table ---
st.subheader("All Recent Data")
st.dataframe(df[["Coin", "Timestamp", "Sentiment", "PriceUSD", "SuggestedAction"]].sort_values("Timestamp", ascending=False).reset_index(drop=True))

# --- Charts for Each Coin ---
st.subheader("Trend Charts")
coins = latest["Coin"].unique().tolist()
for coin in coins:
    cdf = df[df["Coin"] == coin].sort_values("Timestamp")
    st.markdown(f"#### {coin}")
    # Price Chart
    price_chart = alt.Chart(cdf).mark_line().encode(
        x="Timestamp:T",
        y="PriceUSD:Q"
    ).properties(title=f"{coin} - Price")
    # Sentiment Chart
    sent_chart = alt.Chart(cdf).mark_line(color="orange").encode(
        x="Timestamp:T",
        y="Sentiment:Q"
    ).properties(title=f"{coin} - Sentiment")
    st.altair_chart(price_chart, use_container_width=True)
    st.altair_chart(sent_chart, use_container_width=True)

# --- (Optionally) Show all history ---
if not hist.empty:
    st.subheader("Full Sentiment History")
    st.dataframe(hist.sort_values("Timestamp", ascending=False).reset_index(drop=True))

st.success("Dashboard loaded and rendered successfully.")
