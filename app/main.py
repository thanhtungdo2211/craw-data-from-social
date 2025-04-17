import os
import logging
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st
import pandas as pd

from core.get_video_ids_by_query import get_video_ids_by_query
from process import process_video

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv("./.env")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

if __name__ == "__main__":
    # Frontend Streamlit
    st.title("Lấy nội dung YouTube bằng tiếng Việt")

    with st.form("search_form"):
        query = st.text_input("Nhập từ khóa tìm kiếm hoặc tên kênh YouTube (bắt đầu bằng @):", 
                            placeholder="Ví dụ: 'việt tân' hoặc '@VietTan'")
        max_results = st.slider("Số lượng video tối đa:", min_value=1, max_value=50, value=5)
        submitted = st.form_submit_button("Tìm kiếm")

    if submitted and query:
        with st.spinner(f"Đang tìm kiếm video cho '{query}'..."):
            video_ids = get_video_ids_by_query(query, max_results, api_key=YOUTUBE_API_KEY)
        
        if not video_ids:
            st.error("Không tìm thấy video nào cho truy vấn này.")
        else:
            st.success(f"Đã tìm thấy {len(video_ids)} video.")
            
            df = pd.DataFrame(columns=["ID", "URL", "Transcript", "Content"])
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            for i, video_id in enumerate(video_ids):
                status_text.text(f"Đang xử lý video {i+1}/{len(video_ids)}: {video_id}")
                
                result = process_video(video_id)
                results.append(result)
                
                progress_bar.progress((i + 1) / len(video_ids))
                
            status_text.empty()
            progress_bar.empty()
            
            df = pd.DataFrame(results, columns=["ID", "URL", "Transcript", "Content"])
            
            # Show result
            st.dataframe(df)
            
            if st.button("Tải xuống dạng CSV"):
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Tải xuống",
                    data=csv,
                    file_name=f"youtube_results_{query.replace(' ', '_')}.csv",
                    mime="text/csv",
                )