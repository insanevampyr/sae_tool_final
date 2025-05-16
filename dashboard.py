# dashboard.py
import os, json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone, timedelta
from send_telegram import send_telegram_message
from fetch_prices import fetch_prices

# --- Page config ---
st.set_page_config(page_title='AlphaPulse', layout='wide')
st.image('alpha_logo.jpg', use_container_width=True)
st.title('📊 AlphaPulse: Crypto Sentiment Dashboard')
st.markdown('Live crypto sentiment analysis, historical trends, and ML forecasts.')

# --- Load data ---
def load_data(path): return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
def load_json(path):
    if os.path.exists(path):
        try: return json.load(open(path,'r',encoding='utf-8'))
        except json.JSONDecodeError: return {}
    return {}

def save_json(data,path): json.dump(data,open(path,'w',encoding='utf-8'),indent=2)

csv_path='sentiment_output.csv'
history_path='sentiment_history.csv'
ml_log_path='prediction_log.json'
actions_path='previous_actions.json'

raw=load_data(csv_path)
hist=load_data(history_path)
log=load_json(ml_log_path)
actions=load_json(actions_path)
prices=fetch_prices()
now=datetime.now(timezone.utc)

# --- Sidebar: sentiment summary ---
st.sidebar.header('📌 Sentiment Summary')
ranges=['Last 24 Hours','Last 7 Days','Last 30 Days']
cutoff={r: now-timedelta(days=1 if i==0 else 7 if i==1 else 30) for i,r in enumerate(ranges)}
sel=st.sidebar.selectbox('Summary window:',ranges)
raw['Timestamp']=pd.to_datetime(raw['Timestamp'],utc=True,errors='coerce') if 'Timestamp' in raw.columns else None
recent=raw[raw['Timestamp']>=cutoff[sel]] if not raw.empty else raw
if recent.empty and not raw.empty: st.sidebar.warning(f'No data in {sel}; showing all.'); recent=raw
for coin,avg in recent.groupby('Coin')['Sentiment'].mean().items():
    action='📈 Buy' if avg>0.2 else '📉 Sell' if avg<-0.2 else '🤝 Hold'
    st.sidebar.write(f'**{coin}:** {avg:.3f} → {action}')
    key=f'alert_{coin}'
    if st.sidebar.checkbox(f'🔔 Alert for {coin}',key=key):
        if actions.get(coin)!=action:
            send_telegram_message(f'⚠️ {coin} now {action} ({avg:.2f})')
            actions[coin]=action; save_json(actions,actions_path)

# --- ML predictions ---
st.markdown('### 🤖 ML Price Predictions')
tol=4
if isinstance(log,dict):
    st.markdown(f'_Tolerance ±{tol}%_')
    shown=False
    for coin,ents in log.items():
        if not ents: continue
        shown=True; e=ents[-1]
        pred=e.get('predicted'); act=e.get('actual'); pct=e.get('diff_pct',0); ok=e.get('accurate')
        ts=e.get('timestamp','').split('+')[0].replace('T',' ')
        icon='✅' if ok else ('❌' if ok==False else '🕒')
        st.markdown(f"""
**{coin}**: Pred ${pred:.2f} ({pct:+.2f}%) at {ts} UTC  
Actual: {('$'+format(act,',.2f')) if act else '_awaiting_'}  
Accuracy: {icon}
""")
    if not shown: st.info('Run analyze.py to append predictions.')
else: st.info('No ML log found.')

# --- Trends ---
st.markdown('### 📈 Trends Over Time')
if not hist.empty:
    hist['Timestamp']=pd.to_datetime(hist['Timestamp'],utc=True,errors='coerce')
    coin=st.selectbox('Select coin:',hist['Coin'].unique())
    df=hist[hist['Coin']==coin]
    fig,ax1=plt.subplots(); ax1.plot(df['Timestamp'],df['Sentiment'],label='Sentiment')
    ax1.set_ylabel('Sentiment')
    ax2=ax1.twinx();
    if 'PriceUSD' in df: ax2.plot(df['Timestamp'],df['PriceUSD'],linestyle='--',label='Price'); ax2.set_ylabel('Price USD')
    ax1.xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
    st.pyplot(fig)
else: st.warning('No history.')

# --- Details ---
st.subheader('📋 Sentiment Details')
if not raw.empty:
    df=raw.drop_duplicates(['Timestamp','Coin','Source','Text'])
    st.dataframe(df.sort_values('Timestamp',ascending=False))
else: st.info('No data.')
```
