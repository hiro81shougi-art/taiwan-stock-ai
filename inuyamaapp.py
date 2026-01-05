import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import feedparser # 新聞抓取工具

# --- 1. 頁面設定 ---
st.set_page_config(page_title="隨身AI台股戰情室", layout="wide")
st.title("📈 隨身 AI 台股戰情室")

# --- 2. 側邊欄：我的自選股 & 新手教學 ---
with st.sidebar:
    st.header("❤️ 我的自選股")
    # 這裡設定你的最愛清單
    default_tickers = ['2330', '0050', '2603', '2317', '00878', '0056']
    selected_ticker = st.selectbox("快速選擇：", default_tickers, index=0)
    
    st.write("---")
    # 手動輸入功能
    custom_ticker = st.text_input("或是輸入其他代號 (如 2454)：")
    
    # 決定最終要看哪一支
    if custom_ticker:
        ticker_input = custom_ticker
    else:
        ticker_input = selected_ticker
        
    st.divider()
    st.header("📚 邊看邊學：股市小教室")
    with st.expander("什麼是 K 線 (紅/綠棒)？"):
        st.info("紀錄一天的股價。紅色代表漲（收盤價 > 開盤價），綠色代表跌。柱子越長，代表當天買方或賣方的力道越強。")
    with st.expander("什麼是 月線 (20MA)？"):
        st.info("過去 20 天大家的平均成本。這是重要的「生命線」。\n\n👉 股價在月線上面 = 大家都在賺錢 = 趨勢偏多\n👉 股價在月線下面 = 大家都被套牢 = 趨勢偏空")
    with st.expander("什麼是 RSI 指標？"):
        st.info("用來判斷「有沒有漲過頭/跌過頭」。\n\n👉 超過 70：太熱了，小心有人要賣股票。\n👉 低於 30：太冷了，跌太深可能會反彈。")

ticker = f"{ticker_input}.TW"

# --- 3. AI 新聞解讀功能 ---
def get_ai_news():
    try:
        # 抓取 Yahoo 奇摩股市熱門新聞
        rss_url = "https://tw.stock.yahoo.com/rss?category=tw-market"
        feed = feedparser.parse(rss_url)
        
        news_data = []
        # AI 簡易關鍵字判斷邏輯
        keywords_bull = ['漲', '強', '攻', '高', '多', '旺', '噴', '利多']
        keywords_bear = ['跌', '弱', '挫', '低', '空', '縮', '崩', '利空']
        
        for entry in feed.entries[:5]: # 只抓最新的 5 則
            title = entry.title
            link = entry.link
            
            # 判斷情緒
            sentiment = "😐 中性/一般"
            color = "#777777" # 灰色
            
            if any(k in title for k in keywords_bull):
                sentiment = "🔥 利多/強勢"
                color = "#FF4B4B" # 紅色
            elif any(k in title for k in keywords_bear):
                sentiment = "🥶 利空/弱勢"
                color = "#00C853" # 綠色
                
            news_data.append({"title": title, "sentiment": sentiment, "link": link, "color": color})
        return news_data
    except:
        return []

# --- 4. 顯示新聞區塊 ---
st.subheader("📰 今日台股焦點 & AI 關鍵字快篩")
with st.expander("點擊展開最新新聞分析", expanded=True):
    news_list = get_ai_news()
    if news_list:
        for news in news_list:
            # 顯示彩色標籤
            st.markdown(f"<span style='background-color:{news['color']}; color:white; padding:2px 6px; border-radius:4px; font-size:12px'>{news['sentiment']}</span> <a href='{news['link']}' target='_blank' style='text-decoration:none; color:inherit; font-weight:bold'>{news['title']}</a>", unsafe_allow_html=True)
            st.write("") # 空行
    else:
        st.write("目前無法取得新聞，請稍後再試。")

st.divider()

# --- 5. 抓取股價數據 ---
@st.cache_data
def get_data(symbol):
    try:
        df = yf.download(symbol, period="6mo")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

# --- 6. 計算指標 ---
def calculate_indicators(df):
    df['MA20'] = df['Close'].rolling(window=20).mean() # 月線
    
    # RSI 計算
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

# --- 7. 主畫面顯示 ---
if ticker_input:
    df = get_data(ticker)
    
    if df is not None and not df.empty:
        df = calculate_indicators(df)
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        change = latest['Close'] - prev['Close']
        color_trend = "red" if change > 0 else "green"
        
        # 標題區
        st.header(f"📊 {ticker_input} 個股分析")
        
        # 數據儀表板
        col1, col2, col3 = st.columns(3)
        col1.metric("最新收盤價", f"{latest['Close']:.1f}")
        col1.markdown(f"漲跌：<span style='color:{color_trend}; font-size:20px; font-weight:bold'>{change:.1f}</span>", unsafe_allow_html=True)
        col2.metric("RSI 強弱指數", f"{latest['RSI']:.1f}")
        col3.metric("月線 (20MA)", f"{latest['MA20']:.1f}")
        
        st.divider()
        
        # AI 判讀區 (你的隨身分析師)
        st.subheader("🤖 AI 戰情室：動向解讀")
        
        # 1. 趨勢判斷
        if latest['Close'] > latest['MA20']:
            st.success(f"🔥 **多頭格局 (偏強)**\n\n股價 ({latest['Close']:.1f}) 成功站上月線，這代表最近一個月買這檔股票的人大多是賺錢的，主力願意護盤，趨勢向上。")
        else:
            st.error(f"🥶 **空頭格局 (偏弱)**\n\n股價 ({latest['Close']:.1f}) 跌破月線，這代表最近一個月買的人都被套牢了，上方賣壓很重，趨勢向下。")
            
        # 2. RSI 判斷
        if latest['RSI'] > 75:
            st.warning("⚠️ **過熱警示**：RSI 指標太高了！大家都在搶買，這時候反而容易出現「獲利了結」的賣壓，千萬不要亂追高。")
        elif latest['RSI'] < 25:
            st.info("💎 **超賣訊號**：RSI 指標太低了！短線殺過頭，可能會有反彈撿便宜的機會，但還是要設好停損。")
        else:
            st.info("😐 **行情普通**：目前買賣力道很平均，沒有特別過熱或過冷，可以搭配其他指標觀察。")

        # K線圖
        st.divider()
        st.subheader("📉 互動走勢圖 (可縮放)")
        fig = go.Figure(data=[
            go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'),
            go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=2), name='月線 (20MA)')
        ])
        fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.error("找不到資料，請確認代號是否正確。")