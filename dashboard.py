# dashboard.py
from dotenv import load_dotenv
load_dotenv()

import os, json
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
import altair as alt

# ─── CONFIG ────────────────────────────────────────────────────────────────
COINS         = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
HIST_CSV      = "sentiment_history.csv"
PRED_LOG_JSON = "prediction_log.json"
LOGO_FILE     = "alpha_logo.jpg"

# ─── HELPERS ───────────────────────────────────────────────────────────────
@st.cache_data
def load_history() -> pd.DataFrame:
    if not os.path.exists(HIST_CSV):
        return pd.DataFrame(columns=[
            "Timestamp","Coin","Source","Sentiment","PriceUSD","SuggestedAction"
        ])
    df = pd.read_csv(HIST_CSV)
    # force proper datetime & UTC
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    return df.dropna(subset=["Timestamp"])

@st.cache_data
def load_predictions() -> dict:
    if not os.path.exists(PRED_LOG_JSON):
        return {c: [] for c in COINS}
    with open(PRED_LOG_JSON,"r",encoding="utf-8") as f:
        return json.load(f)

# ─── PAGE SETUP ────────────────────────────────────────────────────────────
st.set_page_config(page_title="AlphaPulse", layout="wide")

# --- logo (centered) ---
if os.path.exists(LOGO_FILE):
    st.markdown(
        f"<div style='text-align:center'>"
        f"<img src='{LOGO_FILE}' style='max-width:300px'/>"
        f"</div>",
        unsafe_allow_html=True
    )

# ─── SIDEBAR ────────────────────────────────────────────────────────────────
st.sidebar.header("📌 Sentiment Summary")

window = st.sidebar.selectbox(
    "Summary window",
    ["Last 24 Hours","Last 7 Days","Last 30 Days"],
    index=0
)

hist   = load_history()
now    = datetime.now(timezone.utc)
if window=="Last 24 Hours":
    cutoff = now - pd.Timedelta(hours=24)
elif window=="Last 7 Days":
    cutoff = now - pd.Timedelta(days=7)
else:
    cutoff = now - pd.Timedelta(days=30)

recent = hist[hist.Timestamp >= cutoff]

if hist.empty:
    st.sidebar.info("No data yet.")
else:
    st.sidebar.info(f"Data newest at {hist.Timestamp.max()}")

for coin in COINS:
    dfc   = recent[recent.Coin==coin]
    avg   = dfc.Sentiment.mean() if not dfc.empty else float("nan")
    action = "🤝 Hold" if abs(avg)<0.2 else ("📈 Buy" if avg>0 else "📉 Sell")
    color  = "green" if avg>0 else ("red" if avg<0 else "black")
    st.sidebar.markdown(
        f"**{coin}**: <span style='color:{color}'>{avg:+.3f}</span> → {action}",
        unsafe_allow_html=True
    )

# ─── MAIN ──────────────────────────────────────────────────────────────────
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")

# --- Next-Hour Forecasts as cards ---
st.subheader("🤖 Next-Hour Price Forecasts")
plog = load_predictions()
cols = st.columns(len(COINS), gap="small")
for col, coin in zip(cols, COINS):
    entries = plog.get(coin, [])
    if not entries:
        col.write(f"**{coin}**")  
        col.info("No data yet")
        continue

    last      = entries[-1]
    now_p      = last.get("current", 0.0)
    pred_p     = last.get("predicted",0.0)
    ts         = last.get("timestamp","")[-5:]  # hh:mm
    acc        = last.get("accurate", None)
    delta_pct  = (pred_p - now_p)/now_p*100 if now_p else 0
    delta_str  = f"{delta_pct:+.1f}%"
    delta_color= "normal" if abs(delta_pct)<0.1 else ("positive" if delta_pct>0 else "negative")

    col.metric(
        label=f"**{coin}** by {ts}",
        value=f"${pred_p:.2f}",
        delta=delta_str,
        delta_color=delta_color
    )
    col.caption(f"Now: ${now_p:.2f}  •  {acc*100:.0f}% acc (24h)" if acc is not None else "")

# ─── Trends Over Time ░──────────────────────────────────────────────────────
st.subheader("📈 Trends Over Time")
sel = st.selectbox("Select coin:", COINS)
dfc = hist[hist.Coin==sel].sort_values("Timestamp")
if dfc.empty:
    st.info("No data for this coin yet.")
else:
    base = alt.Chart(dfc).encode(x=alt.X("Timestamp:T", title=None))
    price_line = base.mark_line(color="#66c2a5").encode(
        y=alt.Y("PriceUSD:Q", title="Price (USD)")
    )
    sent_line = base.mark_line(color="#fc8d62").encode(
        y=alt.Y("Sentiment:Q", title="Sentiment", axis=alt.Axis(orient="right"))
    )
    layered = alt.layer(price_line, sent_line).resolve_scale(y="independent")
    st.altair_chart(layered, use_container_width=True)

# ─── FOOTER ────────────────────────────────────────────────────────────────
if not hist.empty:
    st.caption(f"Last updated: {hist.Timestamp.max()} UTC")
