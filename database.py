import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import streamlit as st

# 定義工作表名稱
SHEET_REPORTS = "Reports"
SHEET_COMPARISONS = "Comparisons"

def _get_connection():
    """建立 Google Sheets 連線"""
    # 從 secrets 讀取憑證
    # 注意：Streamlit Cloud 的 secrets 會把 TOML 的結構轉為 dict
    # 這裡我們利用 st.secrets 直接建立憑證物件
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # 組合 secrets 裡的資訊變成 dict
    creds_dict = {
        "type": st.secrets["type"],
        "project_id": st.secrets["project_id"],
        "private_key_id": st.secrets["private_key_id"],
        "private_key": st.secrets["private_key"],
        "client_email": st.secrets["client_email"],
        "client_id": st.secrets["client_id"],
        "auth_uri": st.secrets["auth_uri"],
        "token_uri": st.secrets["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["client_x509_cert_url"]
    }
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # 開啟試算表
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    return client.open_by_url(sheet_url)

def init_db():
    """初始化資料庫 (檢查工作表是否存在，不存在則建立並寫入標題)"""
    try:
        sh = _get_connection()
        
        # 1. 初始化 Reports 表
        try:
            ws = sh.worksheet(SHEET_REPORTS)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=SHEET_REPORTS, rows=100, cols=10)
            # 寫入標題列
            ws.append_row(["channel", "video_id", "title", "date", "content", "url", "created_at"])

        # 2. 初始化 Comparisons 表
        try:
            ws = sh.worksheet(SHEET_COMPARISONS)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=SHEET_COMPARISONS, rows=100, cols=10)
            # 寫入標題列
            ws.append_row(["title", "content", "ref_gooaye", "ref_miula", "created_at"])
            
    except Exception as e:
        st.error(f"Google Sheets 連線失敗: {e}")

def check_video_exists(video_id):
    try:
        sh = _get_connection()
        ws = sh.worksheet(SHEET_REPORTS)
        # 讀取所有 video_id 欄位 (假設在第2欄)
        video_ids = ws.col_values(2) 
        return video_id in video_ids
    except Exception as e:
        print(f"Check Exists Error: {e}")
        return False

def save_report(channel, video_id, title, content, url, publish_date):
    try:
        sh = _get_connection()
        ws = sh.worksheet(SHEET_REPORTS)
        # 依序對應標題列: channel, video_id, title, date, content, url, created_at
        row = [
            channel, 
            video_id, 
            title, 
            publish_date, 
            content, 
            url, 
            str(datetime.now())
        ]
        ws.append_row(row)
        return True
    except Exception as e:
        print(f"Sheet Save Error: {e}")
        return False

def save_comparison(title, content, ref_gooaye, ref_miula):
    try:
        sh = _get_connection()
        ws = sh.worksheet(SHEET_COMPARISONS)
        # 依序對應: title, content, ref_gooaye, ref_miula, created_at
        row = [
            title, 
            content, 
            ref_gooaye, 
            ref_miula, 
            str(datetime.now())
        ]
        ws.append_row(row)
        return True
    except Exception as e:
        print(f"Sheet Comparison Save Error: {e}")
        return False

def get_all_reports():
    """取得所有個別分析 (按影片日期排序)"""
    try:
        sh = _get_connection()
        ws = sh.worksheet(SHEET_REPORTS)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            # 確保日期格式正確以便排序
            df = df.sort_values(by="date", ascending=False)
        return df
    except Exception as e:
        print(f"Get Reports Error: {e}")
        return pd.DataFrame()

def get_all_comparisons():
    """取得所有對照分析 (按生成時間排序)"""
    try:
        sh = _get_connection()
        ws = sh.worksheet(SHEET_COMPARISONS)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            df = df.sort_values(by="created_at", ascending=False)
        return df
    except Exception as e:
        print(f"Get Comparisons Error: {e}")
        return pd.DataFrame()

def get_latest_report_by_channel(channel):
    try:
        df = get_all_reports()
        if df.empty:
            return None
        
        # 篩選特定頻道
        channel_df = df[df['channel'] == channel]
        
        if not channel_df.empty:
            return channel_df.iloc[0]
        return None
    except Exception as e:
        print(f"Get Latest Error: {e}")
        return None