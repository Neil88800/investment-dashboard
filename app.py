import streamlit as st
import core
import database
import os
import markdown
from datetime import datetime

# 初始化
st.set_page_config(page_title="投資情報戰情室", layout="wide")
database.init_db()

st.sidebar.title("🚀 投資戰情室")
page = st.sidebar.radio("功能選擇", ["📊 戰情儀表板 (執行)", "🗃️ 歷史資料庫", "⚖️ 趨勢與對照"])

CHANNELS = [
    {"name": "股癌 Gooaye", "url": "https://www.youtube.com/@Gooaye"},
    {"name": "M觀點 MiuLa", "url": "https://www.youtube.com/@miulaviewpoint"}
]

# --- HTML 生成邏輯 (從 export_html.py 整合而來) ---
def generate_html_report():
    # 注意：CSS 部分的花括號都改成了雙層 {{ }}，唯獨最下方的 {now} 保持單層
    html_template_head = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>投資分析報告匯總</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; }}
            .card {{ background: white; border-radius: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 25px; }}
            h1 {{ color: #2c3e50; text-align: center; }}
            h2 {{ color: #e74c3c; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 0; }}
            h3 {{ color: #3498db; margin-top: 20px; }}
            .meta {{ font-size: 0.85em; color: #7f8c8d; margin-bottom: 15px; }}
            .tag {{ display: inline-block; background: #eee; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-right: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; display: block; overflow-x: auto; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            blockquote {{ border-left: 4px solid #3498db; margin: 0; padding-left: 15px; color: #555; background: #f1f8ff; padding: 10px; }}
        </style>
    </head>
    <body>
        <h1>📈 投資分析資料庫匯總</h1>
        <p style="text-align: center; color: #7f8c8d;">生成時間: {now}</p>
    """
    
    html_content = html_template_head.format(now=datetime.now().strftime("%Y-%m-%d %H:%M"))
    
    # 1. 讀取比較報告
    df_comp = database.get_all_comparisons()
    if not df_comp.empty:
        html_content += "<div class='section-header'><h2>⚔️ 多空對決 / 交叉比對</h2></div>"
        for _, row in df_comp.iterrows():
            html_body = markdown.markdown(row['content'], extensions=['tables', 'fenced_code'])
            html_content += f"""
            <div class="card">
                <div class="meta">📅 分析時間: {row['created_at']}</div>
                <h2>{row['title'] or '未命名報告'}</h2>
                <div class="content">{html_body}</div>
            </div>
            """

    # 2. 讀取單集報告
    df_reports = database.get_all_reports()
    if not df_reports.empty:
        html_content += "<div class='section-header'><h2>📺 單集詳細分析</h2></div>"
        for _, row in df_reports.iterrows():
            html_body = markdown.markdown(row['content'], extensions=['tables', 'fenced_code'])
            html_content += f"""
            <div class="card">
                <div class="meta"><span class="tag">{row['channel']}</span> 📅 上傳日期: {row['date']}</div>
                <h3>{row['title']}</h3>
                <div class="content">{html_body}</div>
                <p><a href="{row['url']}" target="_blank">🔗 觀看原始影片</a></p>
            </div>
            """

    html_content += "</body></html>"
    return html_content

# --- 分析流程 ---
def run_analysis_pipeline(channel_config, status_container, progress_bar):
    try:
        name = channel_config['name']
        url = channel_config['url']
        
        status_container.info(f"📡 [{name}] 正在掃描最新內容...")
        video = core.get_latest_video_robust(url)
        
        if not video:
            status_container.error(f"❌ [{name}] 找不到公開影片。")
            return None

        if database.check_video_exists(video.yt_videoid):
            progress_bar.progress(100)
            status_container.success(f"✅ [{name}] {video.upload_date}「{video.title}」已存在！")
            return {"title": video.title, "skipped": True}

        status_container.warning(f"🚀 [{name}] 發現新影片 ({video.upload_date})：{video.title}，開始處理...")
        st.write(f"🔗 [影片連結]({video.link})")
        progress_bar.progress(30)
        
        status_container.info(f"⬇️ [{name}] 下載音訊中...")
        audio_path = core.download_audio(video.link)
        
        if not audio_path:
            status_container.error(f"❌ [{name}] 音訊下載失敗。")
            return None
        
        progress_bar.progress(60)

        status_container.info(f"🤖 [{name}] AI 正在聆聽並分析...")
        analysis = core.analyze_video(video.title, audio_path, name)
        progress_bar.progress(90)
        
        database.save_report(name, video.yt_videoid, video.title, analysis, video.link, video.upload_date)
        
        try: os.remove(audio_path)
        except: pass
        
        progress_bar.progress(100)
        status_container.success(f"🎉 [{name}] 分析完成！已寫入資料庫。")
        
        return {"title": video.title, "content": analysis, "skipped": False}
    except Exception as e:
        status_container.error(f"系統錯誤: {e}")
        return None

# === 頁面 1: 戰情儀表板 ===
if page == "📊 戰情儀表板 (執行)":
    st.title("📊 投資情報戰情室")
    st.markdown("### 🚀 全局指令")
    if st.button("🔥 一鍵掃描所有頻道 (自動略過舊片)", type="primary", use_container_width=True):
        st.divider()
        for ch in CHANNELS:
            st.subheader(f"📺 檢查：{ch['name']}")
            status = st.empty()
            prog = st.progress(0)
            result = run_analysis_pipeline(ch, status, prog)
            if result and not result.get("skipped"):
                with st.expander(f"查看 {ch['name']} 最新分析報告", expanded=True):
                    st.markdown(result["content"])
            st.divider()
        st.success("✅ 所有頻道檢查完畢！")

    st.markdown("### 📺 個別頻道操作")
    col1, col2 = st.columns(2)
    for i, ch in enumerate(CHANNELS):
        with (col1 if i % 2 == 0 else col2):
            with st.container(border=True):
                st.subheader(ch['name'])
                if st.button(f"檢查 {ch['name']}", key=ch['name']):
                    status = st.empty()
                    prog = st.progress(0)
                    res = run_analysis_pipeline(ch, status, prog)
                    if res and not res.get("skipped"):
                        st.markdown(res["content"])

# === 頁面 2: 歷史資料庫 (含匯出) ===
elif page == "🗃️ 歷史資料庫":
    st.title("🗃️ 歷史情報資料庫")
    
    # --- 新增: 匯出按鈕 ---
    col_dl, _ = st.columns([2, 5])
    with col_dl:
        html_data = generate_html_report()
        st.download_button(
            label="📥 下載完整 HTML 報表",
            data=html_data,
            file_name=f"Investment_Report_{datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html",
            type="primary"
        )
    
    tab1, tab2 = st.tabs(["📺 個別影片報告", "⚔️ 多空戰略報告"])
    
    with tab1:
        df = database.get_all_reports()
        if not df.empty:
            col_filter, col_stat = st.columns([3, 1])
            with col_filter:
                selected_channel = st.selectbox("篩選頻道", ["全部"] + list(df['channel'].unique()))
            with col_stat:
                st.metric("總報告數", len(df))

            if selected_channel != "全部":
                df = df[df['channel'] == selected_channel]
            
            st.dataframe(
                df[['date', 'channel', 'title']], 
                column_config={"date": "影片發布日", "title": "影片標題"},
                use_container_width=True
            )
            
            st.write("---")
            df['label'] = df.apply(lambda x: f"[{x['date']}] {x['title']}", axis=1)
            selected_label = st.selectbox("選擇報告閱讀", df['label'].tolist())
            
            if selected_label:
                record = df[df['label'] == selected_label].iloc[0]
                st.info(f"📅 發布日: {record['date']} | 📺 {record['channel']}")
                st.markdown(record['content'])
                st.markdown(f"🔗 [原始影片連結]({record['url']})")
        else:
            st.info("尚無資料。")

    with tab2:
        df_comp = database.get_all_comparisons()
        if not df_comp.empty:
            st.dataframe(
                df_comp[['created_at', 'title']], 
                column_config={"created_at": "分析時間", "title": "戰略標題"},
                use_container_width=True
            )
            st.write("---")
            selected_comp = st.selectbox("選擇戰略報告", df_comp['title'].tolist())
            
            if selected_comp:
                rec = df_comp[df_comp['title'] == selected_comp].iloc[0]
                with st.expander("🔍 參考來源"):
                    st.text(f"股癌: {rec['ref_gooaye']}\nM觀點: {rec['ref_miula']}")
                st.markdown(rec['content'])
        else:
            st.info("尚無資料。")

# === 頁面 3: 趨勢與對照 ===
elif page == "⚖️ 趨勢與對照":
    st.title("⚖️ 多空對照與趨勢分析")
    st.markdown("抓取資料庫中 **兩大頻道「最新一集」** 報告進行交叉比對。")
    
    col_g, col_m = st.columns(2)
    latest_gooaye = database.get_latest_report_by_channel("股癌 Gooaye")
    latest_miula = database.get_latest_report_by_channel("M觀點 MiuLa")
    
    with col_g:
        st.subheader("股癌 Gooaye (最新)")
        if latest_gooaye is not None:
            st.success(f"📅 {latest_gooaye['date']}\n\n🎬 {latest_gooaye['title']}")
        else:
            st.error("❌ 無資料")
            
    with col_m:
        st.subheader("M觀點 MiuLa (最新)")
        if latest_miula is not None:
            st.success(f"📅 {latest_miula['date']}\n\n🎬 {latest_miula['title']}")
        else:
            st.error("❌ 無資料")

    st.divider()

    if st.button("🚀 生成最新戰略報告", type="primary", use_container_width=True):
        if latest_gooaye is None or latest_miula is None:
            st.error("⚠️ 資料不足：兩位分析師都需要至少有一篇報告。")
        else:
            with st.spinner("AI 正在深度研讀雙方觀點..."):
                result_text = core.compare_trends(latest_gooaye, latest_miula)
                report_title = f"雙雄對決：{latest_gooaye['date']} vs {latest_miula['date']}"
                ref_g = f"[{latest_gooaye['date']}] {latest_gooaye['title']}"
                ref_m = f"[{latest_miula['date']}] {latest_miula['title']}"
                
                database.save_comparison(report_title, result_text, ref_g, ref_m)
                st.success("✅ 分析完成！請至歷史資料庫查看。")
                st.markdown(result_text)