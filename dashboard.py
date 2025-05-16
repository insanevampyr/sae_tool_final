# dashboard.py
from dotenv import load_dotenv
load_dotenv()

import os, json
from datetime import datetime, timezone
import pandas as pd
import streamlit as st

# ─── CONFIG ────────────────────────────────────────────────────────────────
COINS         = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
HIST_CSV      = "sentiment_history.csv"
PRED_LOG_JSON = "prediction_log.json"

# ─── HELPERS ───────────────────────────────────────────────────────────────
@st.cache_data
def load_history() -> pd.DataFrame:
    # if no history yet, return empty frame
    if not os.path.exists(HIST_CSV):
        return pd.DataFrame(columns=[
            "Timestamp","Coin","Source","Sentiment","PriceUSD","SuggestedAction"
        ])
    # read everything in as strings, then coerce the Timestamp
    df = pd.read_csv(HIST_CSV)
    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"], 
        utc=True,            # force UTC tz
        errors="coerce"      # any bad parse → NaT
    )
    return df

@st.cache_data
def load_predictions() -> dict:
    if not os.path.exists(PRED_LOG_JSON):
        return {c: [] for c in COINS}
    with open(PRED_LOG_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

# ─── PAGE LAYOUT ───────────────────────────────────────────────────────────
st.set_page_config(page_title="AlphaPulse", layout="wide")
st.sidebar.header("📌 Sentiment Summary")

# 1) window selector
window = st.sidebar.selectbox(
    "Summary window",
    ["Last 24 Hours", "Last 7 Days", "Last 30 Days"],
    index=0
)

# 2) load & cutoff
hist = load_history()
now = datetime.now(timezone.utc)
if window == "Last 24 Hours":
    cutoff = now - pd.Timedelta(hours=24)
elif window == "Last 7 Days":
    cutoff = now - pd.Timedelta(days=7)
else:
    cutoff = now - pd.Timedelta(days=30)
recent = hist[hist.Timestamp >= cutoff]

# 3) freshness
if hist.empty:
    st.sidebar.info("No data yet.")
else:
    st.sidebar.info(f"Data newest at {hist.Timestamp.max()}")

# 4) per‐coin summary
for coin in COINS:
    dfc = recent[recent.Coin == coin]
    avg = dfc.Sentiment.mean() if not dfc.empty else float("nan")
    action = "🤝 Hold" if abs(avg) < 0.2 else ("📈 Buy" if avg > 0 else "📉 Sell")
    color = "green" if avg > 0 else ("red" if avg < 0 else "black")
    st.sidebar.markdown(
        f"**{coin}**: <span style='color:{color}'>{avg:+.3f}</span> → {action}",
        unsafe_allow_html=True
    )

# ─── MAIN ──────────────────────────────────────────────────────────────────
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")

# 5) ML Price Predictions
st.subheader("🤖 Next-Hour Price Forecasts")
plog = load_predictions()
for coin in COINS:
    entries = plog.get(coin, [])
    if entries:
        last = entries[-1]
        now_price = last.get("current", 0)
        pred      = last.get("predicted", 0)
        ts        = last.get("timestamp", "")[-5:]  # hh:mm
        acc       = last.get("accurate", None)
        arrow     = "▲" if pred > now_price else "▼" if pred < now_price else "→"
        color     = "green" if pred > now_price else "red" if pred < now_price else "black"
        acc_str   = f"  •  {acc*100:.0f}% acc (24h)" if acc is not None else ""
        st.markdown(
            f"**{coin}**  •  Now ${now_price:.2f}  →  **${pred:.2f}** by {ts} UTC  "
            + f"<span style='color:{color}'>{arrow}</span>{acc_str}",
            unsafe_allow_html=True
        )
    else:
        st.markdown(f"**{coin}** → No prediction yet.")

# 6) Trends Over Time
st.subheader("📈 Trends Over Time")
sel = st.selectbox("Select coin:", COINS)
dfc = hist[hist.Coin == sel].set_index("Timestamp").sort_index()
if dfc.empty:
    st.info("No data for this coin yet.")
else:
    dfc = dfc[["Sentiment","PriceUSD"]]
    dfc.columns = ["Sentiment","Price (USD)"]
    st.line_chart(dfc, use_container_width=True)

# 7) Footer
if not hist.empty:
    st.caption(f"Last updated: {hist.Timestamp.max()} UTC")
