import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- Page Setup (Must be first) ---
st.set_page_config(page_title="Alpha Terminal Pro", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

# --- Session State for Login & Theme ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if 'theme' not in st.session_state:
    st.session_state['theme'] = 'Light' # Default Light Set Kiya Hai

# --- Dynamic CSS Injection based on Theme ---
if st.session_state['theme'] == 'Dark':
    bg_color = "#0b0e14"
    text_color = "#d1d4dc"
    card_bg = "#131722"
    border_color = "#2a2e39"
    gauge_bg = "#131722"
else:
    bg_color = "#f1f5f9"
    text_color = "#1e293b"
    card_bg = "#ffffff"
    border_color = "#cbd5e1"
    gauge_bg = "#ffffff"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&family=Inter:wght@400;600;800&display=swap');
    
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
        font-family: 'Inter', sans-serif;
    }}
    
    /* MOBILE MENU FIX - Keeping Header Visible */
    header {{ background-color: transparent !important; }}
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    
    /* Ticker Tape */
    .ticker-wrap {{
        width: 100%;
        background-color: {card_bg};
        border-bottom: 1px solid {border_color};
        padding: 8px 0;
        overflow: hidden;
        white-space: nowrap;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-top: -20px;
        margin-bottom: 20px;
    }}
    .ticker-text {{
        font-family: 'Roboto Mono', monospace;
        color: #2962ff;
        font-weight: bold;
        font-size: 14px;
        letter-spacing: 1px;
    }}

    /* Metric Cards */
    div[data-testid="metric-container"] {{
        background: {card_bg};
        border: 1px solid {border_color};
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-top: 3px solid #2962ff;
    }}
    div[data-testid="stMetricValue"] {{
        font-family: 'Roboto Mono', monospace;
        font-size: 32px;
        font-weight: 700;
        color: {text_color};
    }}
    div[data-testid="stMetricLabel"] {{
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 12px;
        letter-spacing: 1px;
    }}

    /* Primary Button */
    div.stButton > button:first-child {{
        background: #2962ff;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 10px 20px;
        font-weight: 700;
        width: 100%;
        transition: all 0.2s;
    }}
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {{
        background-color: {card_bg};
        border-right: 1px solid {border_color};
    }}
    </style>
""", unsafe_allow_html=True)

# ================= ADVANCED INDICATOR LOGIC =================
def calculate_trend_pinescript(df):
    if df is None or df.empty or len(df) < 200:
        return "Not Enough Data"
    try:
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA_100'] = df['Close'].ewm(span=100, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        last_row = df.iloc[-1]
        
        bullishOrder = (last_row['EMA_20'] > last_row['EMA_50']) and (last_row['EMA_50'] > last_row['EMA_100']) and (last_row['EMA_100'] > last_row['EMA_200'])
        bearishOrder = (last_row['EMA_20'] < last_row['EMA_50']) and (last_row['EMA_50'] < last_row['EMA_100']) and (last_row['EMA_100'] < last_row['EMA_200'])
        priceUpOk = last_row['Close'] > last_row['EMA_20']
        priceDnOk = last_row['Close'] < last_row['EMA_20']
        spreadPct = abs(last_row['EMA_20'] - last_row['EMA_200']) / last_row['EMA_200'] * 100
        spreadOk = spreadPct >= 0.2  
        
        volumeOk = True
        if 'Volume' in df.columns and last_row['Volume'] > 0:
            df['Vol_SMA_20'] = df['Volume'].rolling(window=20).mean()
            if not pd.isna(df['Vol_SMA_20'].iloc[-1]):
                volumeOk = last_row['Volume'] > (df['Vol_SMA_20'].iloc[-1] * 1.05)
        
        bullScore = (1 if priceUpOk else 0) + (1 if spreadOk else 0) + (1 if volumeOk else 0)
        bearScore = (1 if priceDnOk else 0) + (1 if spreadOk else 0) + (1 if volumeOk else 0)
        
        if bullishOrder and bullScore >= 2: return "Bullish 🟢"
        elif bearishOrder and bearScore >= 2: return "Bearish 🔴"
        else: return "Sideways ⚪"
    except:
        return "Calculation Error"

# ================= SCANNER FUNCTION =================
def scan_stocks(tickers):
    name_map = {"^NSEI": "NIFTY 50", "^NSEBANK": "BANK NIFTY", "BTC-USD": "BITCOIN", "ETH-USD": "ETHEREUM", "XAUUSD=X": "GOLD", "GC=F": "GOLD FUT"}
    results = []
    
    my_bar = st.progress(0, text="Executing Algorithmic Scan...")
    for i, ticker in enumerate(tickers):
        try:
            stock = yf.Ticker(ticker)
            data_1h = stock.history(period="3mo", interval="1h", raise_errors=False)
            data_15m = stock.history(period="1mo", interval="15m", raise_errors=False)  
            data_5m = stock.history(period="1mo", interval="5m", raise_errors=False)    
            
            trend_1h = calculate_trend_pinescript(data_1h)
            trend_15m = calculate_trend_pinescript(data_15m)
            trend_5m = calculate_trend_pinescript(data_5m)
            ltp_val = data_5m['Close'].iloc[-1] if (data_5m is not None and not data_5m.empty) else 0.0
            
            signal = "Wait ⏳"
            if "Bullish" in trend_1h and "Bullish" in trend_15m and "Bullish" in trend_5m: signal = "STRONG BUY 🚀"
            elif "Bearish" in trend_1h and "Bearish" in trend_15m and "Bearish" in trend_5m: signal = "STRONG SELL 📉"
                
            results.append({
                "Asset": name_map.get(ticker, ticker.replace(".NS", "")),
                "LTP": f"{ltp_val:.2f}",
                "1H Trend": trend_1h,
                "15m Trend": trend_15m,
                "5m Trend": trend_5m,
                "Signal": signal
            })
        except:
            pass
        my_bar.progress((i + 1) / len(tickers), text=f"Processing {name_map.get(ticker, ticker)}...")
    my_bar.empty()
    return pd.DataFrame(results)

# --- Plotly Speedometer Gauge ---
def create_gauge(buy_count, sell_count, total, bg_col, txt_col):
    if total == 0: total = 1
    score = 50 + ((buy_count - sell_count) / total) * 50 
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        number = {'suffix': "%", 'font': {'color': txt_col}},
        title = {'text': "MARKET SENTIMENT", 'font': {'size': 14, 'color': '#64748b'}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': txt_col, 'visible': False},
            'bar': {'color': txt_col, 'thickness': 0.2},
            'bgcolor': bg_col,
            'borderwidth': 0,
            'steps': [
                {'range': [0, 40], 'color': "rgba(239, 83, 80, 0.4)"},
                {'range': [40, 60], 'color': "rgba(120, 123, 134, 0.2)"},
                {'range': [60, 100], 'color': "rgba(38, 166, 154, 0.4)"}],
        }
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': txt_col, 'family': "Inter"}, height=200, margin=dict(l=10, r=10, t=30, b=10))
    return fig

# --- 1. Login Page ---
def login_page():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown(f"<h1 style='text-align: center; color: {text_color};'>⚡ ALPHA TERMINAL PRO</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            username = st.text_input("QUANT ID")
            password = st.text_input("ACCESS KEY", type="password")
            if st.button("AUTHORIZE"):
                if username == "admin" and password == "12345":
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("Access Denied")

# --- 2. Main Dashboard Page ---
def dashboard_page():
    st.markdown("""
        <div class="ticker-wrap">
            <marquee class="ticker-text" scrollamount="5">
                ● SYSTEM ACTIVE ● MULTI-TIMEFRAME ALIGNMENT ENGINE RUNNING ● 4-EMA CONFLUENCE ACTIVATED ● SCANNING LIQUIDITY ZONES ●
            </marquee>
        </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown(f"<h2 style='color: {text_color}; text-align: center;'>⚡ ALPHA PRO</h2>", unsafe_allow_html=True)
    st.sidebar.markdown("---")
    
    selected_theme = st.sidebar.radio("🌓 THEME", ["Light", "Dark"], index=0 if st.session_state['theme'] == 'Light' else 1)
    if selected_theme != st.session_state['theme']:
        st.session_state['theme'] = selected_theme
        st.rerun()
        
    st.sidebar.markdown("---")
    market_choice = st.sidebar.radio("🌐 SELECT ASSET CLASS", ["NSE Indices", "NSE Equities", "Cryptocurrency", "Commodities/Forex"])
    
    if market_choice == "NSE Indices": active_tickers = ["^NSEI", "^NSEBANK"]
    elif market_choice == "Cryptocurrency": active_tickers = ["BTC-USD", "ETH-USD"]
    elif market_choice == "Commodities/Forex": active_tickers = ["XAUUSD=X", "GC=F"] 
    else:
        active_tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "ITC.NS", "HDFCBANK.NS", "SBIN.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "BAJAJ-AUTO.NS", "SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS"]

    st.sidebar.markdown("---")
    
    # 💥 THE FIX: AUTO REFRESH IS NOW 'TRUE' BY DEFAULT 💥
    auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh (60s)", value=True)
    if auto_refresh: st_autorefresh(interval=60000, limit=None, key="data_refresh_timer")
        
    run_button = st.sidebar.button("INITIALIZE SCAN 🚀")
    
    # SCAN WILL RUN AUTOMATICALLY NOW
    if run_button or auto_refresh:
        result_df = scan_stocks(active_tickers)
        buy_signals = len(result_df[result_df['Signal'] == "STRONG BUY 🚀"])
        sell_signals = len(result_df[result_df['Signal'] == "STRONG SELL 📉"])
        
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1.5])
        with col1: st.metric("TOTAL SCANNED", f"{len(result_df)}")
        with col2: st.metric("BULLISH SETUPS", buy_signals)
        with col3: st.metric("BEARISH SETUPS", sell_signals)
        with col4: 
            fig = create_gauge(buy_signals, sell_signals, len(result_df), gauge_bg, text_color)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown(f"<h4 style='color: {text_color}; margin-top: -20px;'>🔔 PRIME TRADE SETUPS</h4>", unsafe_allow_html=True)
        actionable_df = result_df[result_df['Signal'].isin(["STRONG BUY 🚀", "STRONG SELL 📉"])]
        
        def color_signal_pro(val):
            if isinstance(val, str):
                if "STRONG BUY" in val: return 'background-color: rgba(38, 166, 154, 0.2); color: #00897b; font-weight: bold;'
                elif "STRONG SELL" in val: return 'background-color: rgba(239, 83, 80, 0.2); color: #e53935; font-weight: bold;'
            return ''

        if not actionable_df.empty:
            styled_actionable = actionable_df.style.map(color_signal_pro, subset=['Signal'])
            st.dataframe(styled_actionable, use_container_width=True, hide_index=True)
        else:
            st.markdown(f"<div style='background: {card_bg}; padding: 15px; border-radius: 8px; border: 1px dashed {border_color}; color: #64748b; text-align: center;'>No Prime MTF Alignments Currently Active. Monitoring Market...</div>", unsafe_allow_html=True)

        st.markdown(f"<br><h4 style='color: {text_color};'>📊 RAW SCAN DATA</h4>", unsafe_allow_html=True)
        styled_df = result_df.style.map(color_signal_pro, subset=['Signal'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

    st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
    if st.sidebar.button("DISCONNECT"):
        st.session_state['logged_in'] = False
        st.rerun()

if not st.session_state['logged_in']:
    login_page()
else:
    dashboard_page()
