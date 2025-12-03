import json
import sqlite3
import os

# 1. 設定檔案名稱
json_filename = 'F-A0010-001.json'
db_filename = 'data.db'

def create_database_from_json():
    # 檢查 JSON 檔案是否存在
    if not os.path.exists(json_filename):
        print(f"找不到檔案: {json_filename}，請確認檔案已在目前目錄中。")
        return

    # 2. 讀取 JSON 檔案
    with open(json_filename, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"JSON 格式錯誤: {e}")
            return

    # 3. 建立 SQLite 連線與表格
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()

    # 如果表格已存在則先刪除，確保資料乾淨
    cursor.execute("DROP TABLE IF EXISTS weather_forecast")

    # 建立表格
    # 我們儲存：地區、日期、天氣狀況、天氣代碼、最高溫、最低溫
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_forecast (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            date TEXT,
            weather_desc TEXT,
            weather_id TEXT,
            max_t INTEGER,
            min_t INTEGER
        )
    ''')

    print("資料庫表格已建立...")

    # 4. 解析 JSON 並插入資料
    try:
        # 根據您提供的檔案結構定位到 location 層級
        locations = data['cwaopendata']['resources']['resource']['data']['agrWeatherForecasts']['weatherForecasts']['location']

        insert_count = 0
        
        for loc in locations:
            location_name = loc['locationName']
            
            # 取得該地區的三種天氣要素：天氣現象(Wx)、最高溫(MaxT)、最低溫(MinT)
            wx_list = loc['weatherElements']['Wx']['daily']
            max_t_list = loc['weatherElements']['MaxT']['daily']
            min_t_list = loc['weatherElements']['MinT']['daily']

            # 使用 zip 將同一天的資料組合在一起
            # 假設這三個列表的長度與日期順序是一致的
            for wx, max_t, min_t in zip(wx_list, max_t_list, min_t_list):
                date = wx['dataDate'] # 日期
                weather_desc = wx['weather'] # 天氣描述 (例如: 多雲短暫雨)
                weather_id = wx['weatherid'] # 天氣代碼
                max_temp = int(max_t['temperature']) # 最高溫
                min_temp = int(min_t['temperature']) # 最低溫

                # 執行 SQL 插入指令
                cursor.execute('''
                    INSERT INTO weather_forecast (location, date, weather_desc, weather_id, max_t, min_t)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (location_name, date, weather_desc, weather_id, max_temp, min_temp))
                
                insert_count += 1

        conn.commit()
        print(f"成功插入 {insert_count} 筆資料！")
        print(f"資料庫檔案已儲存為: {db_filename}")

    except KeyError as e:
        print(f"JSON 結構解析錯誤，找不到鍵值: {e}")
    except Exception as e:
        print(f"發生錯誤: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    create_database_from_json()