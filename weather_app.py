import streamlit as st
import sqlite3
import requests
import pandas as pd
import json
from pathlib import Path

# -- Path setup --
# Get the absolute path to the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
# Define the absolute path for the SQLite database
DB_PATH = SCRIPT_DIR / 'weather_data.db'

def getData():
    # 1. 設定氣象署 API 網址與授權碼
    url = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"
    params = {
        "Authorization": "CWA-114A4CB9-10E0-4135-903D-1AAA89EECEAE",
        "downloadType": "WEB",
        "format": "JSON"
    }
    
    # 2. 抓取資料
    response = requests.get(url, params=params)
    all_weather_data = []

    if response.status_code == 200:
        data = response.json()
       
        
        # 3. 解析複雜的 JSON 結構
        # 路徑：cwaopendata -> dataset -> resources -> resource -> data -> agrWeatherForecasts -> weatherForecasts -> location
        try:
            locations = data['cwaopendata']['resources']['resource']['data']['agrWeatherForecasts']['weatherForecasts']['location']
            
            for loc in locations:
                loc_name = loc['locationName']
                
                # 取得該地區的最高溫與最低溫列表
                # weatherElements 下的結構包含 MaxT (最高溫) 和 MinT (最低溫)
                max_t_list = loc['weatherElements']['MaxT']['daily']
                min_t_list = loc['weatherElements']['MinT']['daily']
                
                # 因為每天都有最高和最低溫，我們假設兩個列表長度一樣，用 zip 一起處理
                for max_item, min_item in zip(max_t_list, min_t_list):
                    date = max_item['dataDate']
                    max_val = max_item['temperature']
                    min_val = min_item['temperature']
                    
                    # 整理成字典格式
                    all_weather_data.append({
                        "location": loc_name,
                        "date": date,
                        "max_t": int(max_val), # 轉成整數方便畫圖
                        "min_t": int(min_val)
                    })
        except KeyError as e:
            st.error(f"JSON 解析錯誤，找不到欄位: {e}")
            
    else:
        st.error(f"取得資料失敗，狀態碼：{response.status_code}")

    return all_weather_data

def create_table(data):
    # 建立 SQLite 資料庫連線
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 為了避免重複執行導致資料堆疊，我們先刪除舊表 (正式環境可視需求調整)
    c.execute("DROP TABLE IF EXISTS weather")
    
    # 建立新表：包含 id, 地區, 日期, 最高溫, 最低溫
    c.execute('''CREATE TABLE IF NOT EXISTS weather
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  location TEXT,
                  date TEXT,
                  max_t INTEGER,
                  min_t INTEGER)''')

    # 插入資料
    for d in data: 
        c.execute("INSERT INTO weather (location, date, max_t, min_t) VALUES (?,?,?,?)", 
                  (d['location'], d['date'], d['max_t'], d['min_t']))
    
    conn.commit()
    conn.close()

def app():
    st.title("一週農業氣象預報 🌡️")

    # 從資料庫撈取資料
    conn = sqlite3.connect(DB_PATH)
    # 使用 Pandas 直接讀取 SQL 比較方便處理
    df = pd.read_sql("SELECT * FROM weather", conn)
    conn.close()

    if not df.empty:
        # 1. 製作下拉式選單，讓使用者選擇地區
        unique_locations = df['location'].unique()
        option = st.selectbox(
            '請選擇地區：',
            unique_locations
        )

        # 2. 根據選擇的地區篩選資料
        filtered_df = df[df['location'] == option]

        # 3. 整理圖表資料
        # 將日期設為 Index (X軸)
        chart_data = filtered_df[['date', 'max_t', 'min_t']].set_index('date')
        
        # 重新命名欄位讓圖表圖例好看一點
        chart_data.columns = ['最高溫 (°C)', '最低溫 (°C)']

        # 4. 畫出折線圖
        st.line_chart(chart_data, color=["#FF5733", "#33C1FF"]) # 自訂顏色：紅、藍
        
        # 額外顯示數據表格 (選用)
        with st.expander("查看詳細數據"):
            st.dataframe(filtered_df[['date', 'location', 'max_t', 'min_t']])
    else:
        st.write("目前資料庫中沒有資料。")

if __name__ == '__main__':
    # 執行順序：先抓資料 -> 存入資料庫 -> 啟動 App
    weather_data = getData()
    if weather_data:
        create_table(weather_data)
        app()