import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import feedparser
import numpy as np 

# --- 1. 頁面設定 ---
st.set_page_config(page_title="隨身AI台股戰情室", layout="wide")
st.title("📈 隨身 AI 台股戰情室")

# --- 2. 股票代號與中文名稱對照表 ---
stock_names = {
    '2330': '台積電', '0050': '元大台灣50', '2603': '長榮海運', 
    '2317': '鴻海', '00878': '國泰永續高股息', '0056': '元大高股息',
    '2454': '聯發科', '2303': '聯電', '2881': '富邦金', '2882': '國泰金',
    '3231': '緯創', '2609': '陽明', '2615': '萬海', '2498': '宏達電'
}

# --- 3. 側邊欄設定 ---
with st.sidebar:
    st.header("❤️ 我的自選股")
    default_tickers = list(stock_names.keys())
    # 選單顯示： 2330 台積電
    selected_ticker = st.selectbox("快速選擇：", default_tickers, format_func=lambda x: f"{x} {stock_names.get(x)}")
    
    st.write("---")
    custom_ticker = st.text_input("或是輸入其他代號 (如 2308)：")
    
    if custom_ticker:
        ticker_input = custom_ticker
    else:
        ticker_input = selected_ticker

# 處理名稱顯示
current_name = stock_names.get(ticker_input, ticker_input) 
ticker = f"{ticker_input}.TW"

# --- 4. 抓取資料函數 (含股息) ---
@st.cache_data
def get_stock_info(symbol):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="6mo")
        
        # 抓配息 (過去4次配息總和，大約等於一年)
        dividends = stock.dividends
        if not dividends.empty:
            last_year_div = dividends.sort_index().tail(4).sum()
        else:
            last_year_div = 0
            
        return df, last_year_div
    except:
        return None, 0

# --- 5. 新聞抓取 ---
def get_ai_news():
    try:
        feed = feedparser.parse("https://tw.stock.yahoo.com/rss?category=tw-market")
        news_data = []
        keywords_bull = ['漲', '強', '攻', '高', '多', '旺', '噴', '利多']
        keywords_bear = ['跌', '弱', '挫', '低', '空', '縮', '崩', '利空']
        
        for entry in feed.entries[:3]: 
            title = entry.title
            link = entry.link
            sentiment = "😐 一般"
            color = "#777777"
            if any(k in title for k in keywords_bull):
                sentiment = "🔥 利多"
                color = "#FF4B4B"
            elif any(k in title for k in keywords_bear):
                sentiment = "🥶 利空"
                color = "#00C853"
            news_data.append({"title": title, "sentiment": sentiment, "link": link, "color": color})
        return news_data
    except:
        return []

# --- 6. 顯示新聞 ---
with st.expander("📰 今日新聞快篩", expanded=True):
    news_list = get_ai_news()
    if news_list:
        for news in news_list:
            st.markdown(f"<span style='background-color:{news['color']}; color:white; padding:2px 6px; border-radius:4px; font-size:12px'>{news['sentiment']}</span> <a href='{news['link']}' target='_blank' style='text-decoration:none; color:inherit; font-weight:bold'>{news['title']}</a>", unsafe_allow_html=True)

st.divider()

# --- 7. 主程式邏輯 ---
if ticker_input:
    df, dividend_sum = get_stock_info(ticker)
    
    if df is not None and not df.empty:
        # 計算指標
        df['MA20'] = df['Close'].rolling(window=20).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        latest = df.iloc[-1]
        change = latest['Close'] - df.iloc[-2]['Close']
        color_trend = "red" if change > 0 else "green"
        
        # 計算殖利率
        yield_rate = (dividend_sum / latest['Close']) * 100 if latest['Close'] > 0 else 0
        
        # --- 標題區 (你要的改動：2330 台積電) ---
        # 如果是已知股票顯示名字，未知的顯示代號
        display_title = f"{ticker_input} {current_name}" if ticker_input != current_name else ticker_input
        st.header(f"📊 {display_title}")
        
        # --- 數據儀表板 (你要的改動：新增股息與殖利率) ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("收盤價", f"{latest['Close']:.1f}")
        col1.markdown(f"漲跌：<span style='color:{color_trend}; font-weight:bold'>{change:.1f}</span>", unsafe_allow_html=True)
        col2.metric("RSI 強弱", f"{latest['RSI']:.1f}")
        col3.metric("近一年配息", f"{dividend_sum:.2f} 元")
        col4.metric("殖利率", f"{yield_rate:.2f}%")
        
        st.divider()

        # --- 趨勢預測 (你要的改動：黃色虛線) ---
        days_to_fit = 20
        forecast_days = 5
        
        slope = 0 
        intercept = 0
        has_prediction = False

        if len(df) > days_to_fit:
            recent_df = df.iloc[-days_to_fit:]
            x = np.arange(len(recent_df))
            y = recent_df['Close'].values
            slope, intercept = np.polyfit(x, y, 1)
            future_x = np.arange(len(recent_df), len(recent_df) + forecast_days)
            future_y = slope * future_x + intercept
            has_prediction = True
            
            trend_str = "📈 上升趨勢" if slope > 0 else "📉 下降趨勢"
            st.subheader(f"🔮 AI 趨勢預測：{trend_str}")
        
        # --- 繪圖區 ---
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='月線'))
        
        # 畫預測線
        if has_prediction:
            last_date = df.index[-1]
            future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=forecast_days, freq='B')
            pred_x_dates = [df.index[-1]] + list(future_dates)
            pred_y_prices = [latest['Close']] + list(future_y)
            
            fig.add_trace(go.Scatter(x=pred_x_dates, y=pred_y_prices, 
                                     line=dict(color='yellow', width=3, dash='dot'), 
                                     name='未來預測軌道'))

        fig.update_layout(xaxis_rangeslider_visible=True, height=400)
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.error("找不到資料")
