# dashboard.py

from dotenv import load_dotenv
load_dotenv()

import os, json
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
import altair as alt

from fetch_prices import fetch_prices

# ─── CONFIG ────────────────────────────────────────────────────────────────
COINS         = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
HIST_CSV      = "sentiment_history.csv"
PRED_LOG_JSON = "prediction_log.json"
LOGO_FILE     = "alpha_logo.jpg"

# ─── HELPERS ────────────────────────────────────────────────────────────────
@st.cache_data
def load_history() -> pd.DataFrame:
    if not os.path.exists(HIST_CSV):
        cols = ["Timestamp","Coin","Source","Sentiment","PriceUSD","SuggestedAction"]
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(HIST_CSV)
    # coerce to timezone-aware datetime
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    return df.dropna(subset=["Timestamp"])

@st.cache_data
def load_predictions() -> dict:
    if not os.path.exists(PRED_LOG_JSON):
        return {c: [] for c in COINS}
    return json.load(open(PRED_LOG_JSON, "r", encoding="utf-8"))

# ─── PAGE SETUP ────────────────────────────────────────────────────────────
st.set_page_config(page_title="AlphaPulse", layout="wide")

# ─── LOGO (centered) ───────────────────────────────────────────────────────
if os.path.exists(LOGO_FILE):
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.image(LOGO_FILE, use_container_width=True)

# ─── SIDEBAR: Sentiment Summary ────────────────────────────────────────────
st.sidebar.header("📌 Sentiment Summary")
hist = load_history()
now  = datetime.now(timezone.utc)

window = st.sidebar.selectbox(
    "Summary window",
    ["Last 24 Hours", "Last 7 Days", "Last 30 Days"],
    index=0
)
if window == "Last 24 Hours":
    cutoff = now - pd.Timedelta(hours=24)
elif window == "Last 7 Days":
    cutoff = now - pd.Timedelta(days=7)
else:
    cutoff = now - pd.Timedelta(days=30)

recent = hist[hist.Timestamp >= cutoff]
if hist.empty:
    st.sidebar.info("No data yet.")
else:
    st.sidebar.info(f"Data newest at {hist.Timestamp.max():%Y-%m-%d %H:%M} UTC")

for coin in COINS:
    dfc    = recent[recent.Coin == coin]
    avg    = dfc.Sentiment.mean() if not dfc.empty else float("nan")
    action = "🤝 Hold" if abs(avg) < 0.2 else ("📈 Buy" if avg > 0 else "📉 Sell")
    color  = "green" if avg > 0 else ("red" if avg < 0 else "black")
    st.sidebar.markdown(
        f"**{coin}**: <span style='color:{color}'>{avg:+.3f}</span> → {action}",
        unsafe_allow_html=True
    )

# ─── MAIN CONTENT ──────────────────────────────────────────────────────────
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")

# ─── Next-Hour Price Forecasts ──────────────────────────────────────────────
st.subheader("🤖 Next-Hour Price Forecasts")
plog       = load_predictions()
cur_prices = fetch_prices()

cols = st.columns(len(COINS), gap="small")
for col, coin in zip(cols, COINS):
    entries = plog.get(coin, [])
    if not entries:
        col.write(f"**{coin}**")
        col.info("No predictions yet")
        continue

    last     = entries[-1]
    pred_p   = last.get("predicted", 0.0)
    ts_short = pd.to_datetime(last["timestamp"], utc=True).strftime("%H:%M")
    now_p    = cur_prices.get(coin, 0.0)

    # % change
    dpct  = last.get("diff_pct",
                     round((pred_p - now_p) / now_p * 100 if now_p else 0, 2))
    delta = f"{dpct:+.1f}%"

    col.metric(
        label=f"**{coin}** by {ts_short}",
        value=f"${pred_p:.2f}",
        delta=delta,
        delta_color="normal",  # + green, – red
    )

    # 24h accuracy
    day_ago = now - pd.Timedelta(hours=24)
    accs = [
        e.get("accurate", False)
        for e in entries
        if pd.to_datetime(e["timestamp"], utc=True) >= day_ago
    ]
    acc24 = f"{sum(accs)/len(accs)*100:.0f}%" if accs else "–"
    col.caption(f"Now: ${now_p:.2f} • {acc24} acc (24h)")

# ─── Trends Over Time (Sentiment vs. Price) ─────────────────────────────────
st.subheader("📈 Trends Over Time")
sel = st.selectbox("Select coin:", COINS, index=0)
dfc = hist[hist.Coin == sel].sort_values("Timestamp")

if dfc.empty:
    st.info("No data for this coin yet.")
else:
    base = alt.Chart(dfc).encode(x=alt.X("Timestamp:T", title=None))
    price_line = base.mark_line(color="#66c5ed").encode(
        y=alt.Y("PriceUSD:Q", title="Price (USD)")
    )
    sent_line = base.mark_line(color="#fa8072").encode(
        y=alt.Y("Sentiment:Q", title="Sentiment", axis=alt.Axis(orient="right"))
    )
    layered = alt.layer(price_line, sent_line).resolve_scale(y="independent")
    st.altair_chart(layered, use_container_width=True)

# ─── FOOTER ────────────────────────────────────────────────────────────────
if not hist.empty:
    st.caption(f"Last updated: {hist.Timestamp.max():%Y-%m-%d %H:%M} UTC")
