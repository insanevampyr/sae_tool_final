import os, json
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from fetch_prices import fetch_prices

# ─── CONFIG ────────────────────────────────────────────────────────────────
COINS       = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
HIST_CSV    = "sentiment_history.csv"
PRED_LOG    = "prediction_log.json"
LOGO        = "alpha_logo.jpg"

st.set_page_config(
    page_title="AlphaPulse",
    layout="wide",
)

# ─── HELPERS ────────────────────────────────────────────────────────────────
@st.cache_data
def load_history():
    if not os.path.exists(HIST_CSV):
        return pd.DataFrame(columns=[
            'Timestamp','Coin','Source','Text','Sentiment','PriceUSD','SuggestedAction','Link'
        ])
    df = pd.read_csv(HIST_CSV)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], utc=True, errors='coerce')
    return df

@st.cache_data
def load_predictions():
    if not os.path.exists(PRED_LOG):
        return {c: [] for c in COINS}
    return json.loads(open(PRED_LOG,'r',encoding='utf-8').read())

# ─── SIDEBAR ────────────────────────────────────────────────────────────────
if os.path.exists(LOGO):
    st.sidebar.image(LOGO, use_container_width=True)

st.sidebar.header("📌 Sentiment Summary")
hist = load_history()
now  = datetime.now(timezone.utc)

# 1) choose window
window = st.sidebar.selectbox(
    "Summary window",
    ["Last 24 Hours","Last 7 Days","Last 30 Days"],
    index=0
)
if window=="Last 24 Hours":
    cutoff = now - pd.Timedelta(hours=24)
elif window=="Last 7 Days":
    cutoff = now - pd.Timedelta(days=7)
else:
    cutoff = now - pd.Timedelta(days=30)

recent = hist[hist.Timestamp >= cutoff]

# 2) freshness
if hist.empty:
    st.sidebar.info("No data yet.")
else:
    st.sidebar.success(f"Data newest at {hist.Timestamp.max():%Y-%m-%d %H:%M} UTC")

# 3) per‐coin avg + suggested
for coin in COINS:
    dfc = recent[recent.Coin==coin]
    avg = dfc.Sentiment.mean() if not dfc.empty else 0.0
    emoji = "🤝" if abs(avg)<0.2 else ("📈" if avg>0 else "📉")
    color = "green" if avg>0 else ("red" if avg<0 else "black")
    st.sidebar.markdown(
        f"**{coin}**: <span style='color:{color}'>{avg:+.3f}</span> {emoji}",
        unsafe_allow_html=True
    )

# ─── MAIN ─────────────────────────────────────────────────────────────────
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")

# 4) ML Price Predictions
st.subheader("🤖 Next-Hour Price Forecasts")
plog = load_predictions()
prices = fetch_prices(COINS)
# compute 24 h accuracy from plog vs actuals
acc24 = {}
# (you’d fill this in by comparing logged actuals in hist)

for coin in COINS:
    p = plog.get(coin,[])[-1] if plog.get(coin) else None
    if p:
        nowp = p['timestamp'][11:16]
        curr = prices.get(coin,0)
        pct   = p['pct']
        arrow = "🔺" if pct>0 else ("🔻" if pct<0 else "➡️")
        color = "green" if pct>0 else ("red" if pct<0 else "black")
        acc_badge = "✅" if p['accurate'] else "⚠️"
        st.markdown(
            f"**{coin}** — now ${curr:.2f}, predict **${p['predicted']:.2f}** "
            f"<span style='color:{color}'>{arrow}{abs(pct):.1f}%</span> by {nowp} UTC  {acc_badge}",
            unsafe_allow_html=True
        )
    else:
        st.markdown(f"**{coin}** — no prediction yet.")

# 5) Dual Trend Chart
st.subheader("📈 Trends Over Time")
coin = st.selectbox("Select coin:", COINS)
dfc  = hist[hist.Coin==coin].set_index('Timestamp')
if not dfc.empty:
    dfc = dfc[["PriceUSD","Sentiment"]].rename(columns={"PriceUSD":"Price"})
    st.line_chart(dfc)

# 6) Recent Headlines & Sentiment
st.subheader("📰 Recent Headlines & Sentiment")
out = recent[["Timestamp","Source","Text","Sentiment","Link"]].copy()
if not out.empty:
    out['Timestamp'] = out['Timestamp'].dt.tz_convert(None).dt.strftime("%m-%d %H:%M")
    st.dataframe(out.sort_values("Timestamp",ascending=False).head(20), use_container_width=True)
else:
    st.info("No articles in this window.")

# 7) Footer
if not hist.empty:
    st.caption(f"Last updated: {hist.Timestamp.max():%Y-%m-%d %H:%M} UTC")
