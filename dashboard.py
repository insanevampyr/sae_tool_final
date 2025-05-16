from dotenv import load_dotenv
load_dotenv()

import os, json
from datetime import datetime, timezone
import pandas as pd
import streamlit as st

# ─── CONFIG ────────────────────────────────────────────────────────────────
COINS         = ["Bitcoin","Ethereum","Solana","Dogecoin"]
HIST_CSV      = "sentiment_history.csv"
PRED_LOG_JSON = "prediction_log.json"
OUT_CSV       = "sentiment_output.csv"
LOGO_PATH     = "alpha_logo.jpg"

# ─── HELPERS ───────────────────────────────────────────────────────────────
@st.cache_data
def load_history():
    if not os.path.exists(HIST_CSV):
        return pd.DataFrame(columns=['Timestamp','Coin','Source','Sentiment','PriceUSD','SuggestedAction'])
    df = pd.read_csv(HIST_CSV, parse_dates=['Timestamp'])
    if df['Timestamp'].dt.tz is None:
        df['Timestamp'] = df['Timestamp'].dt.tz_localize('UTC')
    return df

@st.cache_data
def load_predictions():
    if not os.path.exists(PRED_LOG_JSON):
        return {c:[] for c in COINS}
    return json.load(open(PRED_LOG_JSON,'r',encoding='utf-8'))

@st.cache_data
def load_output():
    if not os.path.exists(OUT_CSV):
        return pd.DataFrame()
    return pd.read_csv(OUT_CSV, parse_dates=['Timestamp'])

# ─── PAGE LAYOUT ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="AlphaPulse", layout="wide")

# Logo (centered)
if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, use_container_width=True)

# Sidebar
st.sidebar.header("📌 Sentiment Summary")
window = st.sidebar.selectbox("Summary window",
    ["Last 24 Hours","Last 7 Days","Last 30 Days"], index=0)

hist = load_history()
now  = datetime.now(timezone.utc)

# cutoff
if window=="Last 24 Hours":
    cutoff = now - pd.Timedelta(hours=24)
elif window=="Last 7 Days":
    cutoff = now - pd.Timedelta(days=7)
else:
    cutoff = now - pd.Timedelta(days=30)
recent = hist[hist.Timestamp >= cutoff]

# freshness
if hist.empty:
    st.sidebar.info("No data yet.")
else:
    st.sidebar.info(f"Data newest at {hist.Timestamp.max().strftime('%Y-%m-%d %H:%M')} UTC")

# per‐coin
for coin in COINS:
    dfc   = recent[recent.Coin==coin]
    avg   = dfc.Sentiment.mean() if not dfc.empty else float('nan')
    action= "🤝 Hold" if abs(avg)<0.2 else ("📈 Buy" if avg>0 else "📉 Sell")
    st.sidebar.write(f"**{coin}**: {avg:+.3f} → {action}")

# ─── MAIN ───────────────────────────────────────────────────────────────────
st.title("📊 AlphaPulse: Crypto Sentiment Dashboard")

# ML Predictions
st.subheader("🤖 ML Price Predictions")
plog = load_predictions()
for coin in COINS:
    ent = plog.get(coin, [])
    if ent:
        last  = ent[-1]
        ts    = last['timestamp'][:16].replace("T"," ")
        pred  = last['predicted']
        diff  = last.get('diff_pct')
        # color‐code arrow
        arrow = "🟢" if last.get('accurate') else ("🔴" if diff is not None else "⚪️")
        pct   = f"{diff:+.2f}%" if diff is not None else ""
        st.markdown(f"**{coin}** • ${pred:.2f} {pct} {arrow} • {ts} UTC")
    else:
        st.markdown(f"**{coin}** • No prediction yet.")

# Trends Over Time (Sentiment + Price)
st.subheader("📈 Trends Over Time")
sel = st.selectbox("Select coin:", COINS)
dfc = hist[hist.Coin==sel].set_index('Timestamp')
if not dfc.empty:
    chart_df = dfc[['Sentiment','PriceUSD']].rename(columns={'PriceUSD':'Price'})
    st.line_chart(chart_df)
else:
    st.write("No data to plot.")

# Recent Headlines & Sentiment
st.subheader("📰 Recent Headlines & Sentiment")
out = load_output().sort_values('Timestamp', ascending=False).head(20)
if not out.empty:
    display = out[['Timestamp','Coin','Source','Action','Link']].copy()
    display['Timestamp'] = display['Timestamp'].dt.strftime("%m-%d %H:%M")
    st.dataframe(display, use_container_width=True)
else:
    st.write("No headlines yet.")

# Footer
if not hist.empty:
    st.caption(f"Last updated: {hist.Timestamp.max().strftime('%Y-%m-%d %H:%M')} UTC")
