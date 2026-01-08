import yt_dlp
import streamlit as st
import google.generativeai as genai
import os
import time
import pathlib
import warnings
from types import SimpleNamespace
from datetime import datetime
import streamlit as st # 用於讀取 secrets

warnings.filterwarnings("ignore")

# 取得 API Key
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    # 這裡改成 print 警告，避免在本機測試時直接 crash
    print("⚠️ 找不到 API Key！請檢查 .streamlit/secrets.toml 設定。")
else:
    genai.configure(api_key=GEMINI_API_KEY)

def format_date(date_str):
    """將 YYYYMMDD 轉為 YYYY-MM-DD"""
    if date_str and len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return datetime.now().strftime("%Y-%m-%d")

def get_latest_video_robust(channel_url):
    urls_to_try = [f"{channel_url}/streams", f"{channel_url}/videos", channel_url]
    
    flat_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlistend': 1,
        'ignoreerrors': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    detail_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
    
    for url in urls_to_try:
        try:
            with yt_dlp.YoutubeDL(flat_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info and len(info['entries']) > 0:
                    video_data = info['entries'][0]
                    if 'id' in video_data and 'title' in video_data:
                        video_id = video_data['id']
                        title = video_data['title']
                        raw_date = video_data.get('upload_date')

                        if not raw_date:
                            try:
                                video_link = f"https://www.youtube.com/watch?v={video_id}"
                                with yt_dlp.YoutubeDL(detail_opts) as ydl_detail:
                                    detail_info = ydl_detail.extract_info(video_link, download=False)
                                    raw_date = detail_info.get('upload_date')
                            except Exception:
                                pass

                        upload_date = format_date(raw_date)
                        return SimpleNamespace(yt_videoid=video_id, title=title, link=f"https://www.youtube.com/watch?v={video_id}", upload_date=upload_date)
        except Exception:
            continue
    return None

def download_audio(url):
    # 增加更強的偽裝標頭
    ydl_opts = {
        'format': 'worstaudio/worst', # 下載最低畫質音訊以節省流量
        'outtmpl': 'temp_%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '64'
        }],
        'quiet': False,  # 開啟 log 以便除錯
        'no_warnings': False,
        # 模擬一般瀏覽器請求
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'nocheckcertificate': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return pathlib.Path(f"temp_{info['id']}.mp3")
    except Exception as e:
        # 關鍵修改：直接在前端顯示錯誤，讓你知道發生什麼事
        st.error(f"⚠️ 下載核心錯誤: {str(e)}")
        print(f"Download Error: {e}")
        return None

def get_gemini_model():
    try:
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in all_models:
            if "gemini-1.5-flash" in m and "latest" not in m: return genai.GenerativeModel(m)
        for m in all_models:
            if "flash" in m: return genai.GenerativeModel(m)
        return genai.GenerativeModel("gemini-1.5-flash")
    except:
        return genai.GenerativeModel("models/gemini-1.5-flash")

def analyze_video(video_title, audio_path, channel_name):
    model = get_gemini_model()
    prompt = f"""
    你是專業投資分析師。請分析「{channel_name}」的影片「{video_title}」。
    【任務】：
    1. 忽略閒聊業配，專注於市場趨勢、經濟數據、個股分析。
    2. 如果是 M觀點(MiuLa)，請特別著重他的「總體經濟數據解讀」與「商業邏輯」。
    【輸出格式 (Markdown)】：
    1. **核心觀點摘要** (3點結論)
    2. **市場趨勢判讀** (多/空/震盪及其理由)
    3. **重點標的與產業** (表格呈現：標的 | 看法 | 理由)
    4. **投資策略建議**
    5. **風險提示**
    請使用繁體中文。
    """
    safety = [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
              {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
              {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
              {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
    
    try:
        myfile = genai.upload_file(audio_path)
        while myfile.state.name == "PROCESSING":
            time.sleep(2)
            myfile = genai.get_file(myfile.name)
        response = model.generate_content([prompt, myfile], safety_settings=safety)
        myfile.delete()
        return response.text
    except Exception as e:
        return f"AI 分析發生錯誤: {e}"

def compare_trends(gooaye_report, miula_report):
    model = get_gemini_model()
    prompt = f"""
    你是資深投資策略總監，熟稔於台股、美股及全球市場，並且每年的投資報酬率都是業界頂尖。以下是兩位分析師「最新一集」的市場觀點報告。
    請根據這兩份資料進行深度交叉比對。
    【資料來源 A：股癌 Gooaye】日期：{gooaye_report['date']}，標題：{gooaye_report['title']}
    內容：{gooaye_report['content']}
    【資料來源 B：M觀點 MiuLa】日期：{miula_report['date']}，標題：{miula_report['title']}
    內容：{miula_report['content']}
    【請產出「多空對照戰略報告」】：
    1. **共識聚焦**：兩人都看好或都擔心的部分。
    2. **觀點分歧**：看法不同的地方。
    3. **綜合投資建議**：結合兩者觀點，散戶目前的最佳策略及投資標的。
    4. **本週關鍵字**：3 個共同關鍵字。
    請使用繁體中文回應。
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:

        return f"對照分析失敗: {e}"
