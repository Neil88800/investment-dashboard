import streamlit as st
import database
import markdown

st.set_page_config(page_title="投資情報戰情室", layout="wide")

# 初始化 (連線 Google Sheets)
try:
    database.init_db()
except:
    st.error("無法連線至資料庫，請檢查 Secrets 設定。")

st.sidebar.title("🚀 投資戰情室")
st.sidebar.info("💡 資料由後端機器人自動更新")

# 這裡移除「執行分析」的按鈕，只保留閱覽功能
page = st.sidebar.radio("功能選擇", ["🗃️ 最新情報庫", "⚖️ 趨勢與對照"])

if page == "🗃️ 最新情報庫":
    st.title("🗃️ 投資情報資料庫")
    
    df = database.get_all_reports()
    if not df.empty:
        # 顯示最新兩筆重點
        st.subheader("🔥 最新熱騰騰報告")
        cols = st.columns(2)
        for i in range(min(2, len(df))):
            row = df.iloc[i]
            with cols[i]:
                st.info(f"📅 {row['date']} | {row['channel']}")
                st.write(f"**{row['title']}**")
                with st.expander("快速預覽"):
                    st.markdown(row['content'][:200] + "...")

        st.divider()
        
        # 詳細查詢區
        col_filter, _ = st.columns([2, 1])
        with col_filter:
            selected_channel = st.selectbox("篩選頻道", ["全部"] + list(df['channel'].unique()))
        
        if selected_channel != "全部":
            df = df[df['channel'] == selected_channel]
        
        # 選擇影片
        df['label'] = df.apply(lambda x: f"[{x['date']}] {x['title']}", axis=1)
        selected_label = st.selectbox("選擇詳細報告", df['label'].tolist())
        
        if selected_label:
            record = df[df['label'] == selected_label].iloc[0]
            st.markdown(f"### 📺 {record['title']}")
            st.caption(f"發布日期: {record['date']} | 來源: {record['channel']}")
            st.markdown(record['content'])
            st.markdown(f"[🔗 點此觀看原始影片]({record['url']})")
    else:
        st.info("資料庫目前為空，請確認後端機器人是否已執行。")

elif page == "⚖️ 趨勢與對照":
    st.title("⚖️ 多空對照與趨勢分析")
    
    # 從資料庫撈取最新報告來做比較
    latest_gooaye = database.get_latest_report_by_channel("股癌 Gooaye")
    latest_miula = database.get_latest_report_by_channel("M觀點 MiuLa")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("股癌 (最新)")
        if latest_gooaye is not None:
            st.success(f"{latest_gooaye['date']} {latest_gooaye['title']}")
        else:
            st.warning("無資料")
            
    with col2:
        st.subheader("M觀點 (最新)")
        if latest_miula is not None:
            st.success(f"{latest_miula['date']} {latest_miula['title']}")
        else:
            st.warning("無資料")
            
    # 這裡的比較功能建議保留，因為它是純文字生成，不會被 YouTube 擋
    if st.button("生成最新戰略比較"):
        import core # 這裡需要 core.py 裡的 compare_trends 函式
        if latest_gooaye is not None and latest_miula is not None:
            with st.spinner("AI 正在分析雙方觀點..."):
                # 注意：雲端的 core.py 此時只需要 compare_trends 函式
                # 你可能需要在雲端保留一個精簡版的 core.py
                res = core.compare_trends(latest_gooaye, latest_miula)
                st.markdown(res)
                database.save_comparison(f"{latest_gooaye['date']} vs {latest_miula['date']}", res, latest_gooaye['title'], latest_miula['title'])
