import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = "investment_data.db"

def init_db():
    """初始化資料庫 (包含個股報告與對照報告)"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. 個別影片分析表
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT,
            video_id TEXT UNIQUE,
            title TEXT,
            date TEXT,
            content TEXT,
            url TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # 2. 多空對照報告表
    c.execute('''
        CREATE TABLE IF NOT EXISTS comparisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            ref_gooaye TEXT,
            ref_miula TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def check_video_exists(video_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM reports WHERE video_id = ?", (video_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def save_report(channel, video_id, title, content, url, publish_date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT OR IGNORE INTO reports (channel, video_id, title, date, content, url, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (channel, video_id, title, publish_date, content, url, datetime.now()))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Save Error: {e}")
        return False
    finally:
        conn.close()

def save_comparison(title, content, ref_gooaye, ref_miula):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO comparisons (title, content, ref_gooaye, ref_miula, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, content, ref_gooaye, ref_miula, datetime.now()))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Save Comparison Error: {e}")
        return False
    finally:
        conn.close()

def get_all_reports():
    """取得所有個別分析 (按影片日期排序)"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM reports ORDER BY date DESC", conn)
    conn.close()
    return df

def get_all_comparisons():
    """取得所有對照分析 (按生成時間排序)"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM comparisons ORDER BY created_at DESC", conn)
    conn.close()
    return df

def get_latest_report_by_channel(channel):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(f"SELECT * FROM reports WHERE channel = '{channel}' ORDER BY date DESC LIMIT 1", conn)
    conn.close()
    if not df.empty:
        return df.iloc[0]
    return None