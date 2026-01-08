import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import streamlit as st

# 定義工作表名稱
SHEET_REPORTS = "Reports"
SHEET_COMPARISONS = "Comparisons"

def _get_connection():
    """建立 Google Sheets 連線 (修正版：支援巢狀 Secrets 讀取)"""
    
    # 1. 判斷 Secrets 的位置
    # 如果使用者依照建議設定了 [connections.gsheets]，資料會被包在裡面
    if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
        s = st.secrets["connections"]["gsheets"]
    else:
        # 如果使用者直接把 JSON 貼在最外層
        s = st.secrets

    # 2. 建立憑證字典
    # 注意：private_key 有時候複製貼上會把 \n 變成字串，這裡做個防呆處理
    creds_dict = {
        "type": s["type"],
        "project_id": s["project_id"],
        "private_key_id": s["private_key_id"],
        "private_key": s["private_key"].replace("\\n", "\n"), 
        "client_email": s["client_email"],
        "client_id": s["client_id"],
        "auth_uri": s["auth_uri"],
        "token_uri": s["token_uri"],
        "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
        "client_x509_cert_url": s["client_x509_cert_url"]
    }
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # 3. 開啟試算表
    # 如果 spreadsheet 網址也在 secrets 裡 (依照建議的設定)
    if "spreadsheet" in s:
        return client.open_by_url(s["spreadsheet"])
    else:
        # 相容舊設定或防止找不到 key
        return client.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])

def init_db():
    """初始化資料庫 (檢查工作表是否存在，不存在則建立並寫入標題)"""
    try:
        sh = _get_connection()
        
        # 1. 初始化 Reports 表
        try:
            ws = sh.worksheet(SHEET_REPORTS)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=SHEET_REPORTS, rows=100, cols=10)
            ws.append_row(["channel", "video_id", "title", "date", "content", "url", "created_at"])

        # 2. 初始化 Comparisons 表
        try:
            ws = sh.worksheet(SHEET_COMPARISONS)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=SHEET_COMPARISONS, rows=100, cols=10)
            ws.append_row(["title", "content", "ref_gooaye", "ref_miula", "created_at"])
            
    except Exception as e:
        # 這裡改用 st.error 顯示更詳細的錯誤，方便除錯
        st.error(f"Google Sheets 連線初始化失敗: {e}")

def check_video_exists(video_id):
    try:
        sh = _get_connection()
        ws = sh.worksheet(SHEET_REPORTS)
        video_ids = ws.col_values(2) # 假設 video_id 在第2欄
        return video_id in video_ids
    except Exception as e:
        print(f"Check Exists Error: {e}")
        return False

def save_report(channel, video_id, title, content, url, publish_date):
    try:
        sh = _get_connection()
        ws = sh.worksheet(SHEET_REPORTS)
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
    try:
        sh = _get_connection()
        ws = sh.worksheet(SHEET_REPORTS)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df = df.sort_values(by="date", ascending=False)
        return df
    except Exception as e:
        print(f"Get Reports Error: {e}")
        return pd.DataFrame()

def get_all_comparisons():
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
        channel_df = df[df['channel'] == channel]
        if not channel_df.empty:
            return channel_df.iloc[0]
        return None
    except Exception as e:
        print(f"Get Latest Error: {e}")
        return None
