import os
import logging
import time
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st
import pandas as pd

from core.get_video_ids_by_query import get_video_ids_by_query
from process import process_video
from core.database_utils import get_video_from_db
from worker.schema import TaskStatus

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

def get_latest_status(video_ids):
    """Get lastest status of video from database"""
    results = []
    statuses = []
    for video_id in video_ids:
        db_video = get_video_from_db(video_id)
        if not db_video:
            status = "CHƯA XỬ LÝ"
            url = f"https://www.youtube.com/watch?v={video_id}"
            process_video(video_id)  # Khởi động task nếu chưa có
            statuses.append(status)
            results.append((video_id, url, status, None, None))
        else:
            status = db_video.status
            url = db_video.url
            transcript = db_video.transcript if status == TaskStatus.SUCCESS.value else None
            content = db_video.content if status == TaskStatus.SUCCESS.value else None
            statuses.append(status)
            results.append((video_id, url, status, transcript, content))
    
    # Kiểm tra xem tất cả các video đã xử lý xong chưa
    all_completed = all(status == TaskStatus.SUCCESS.value for status in statuses)
    return results, all_completed

if __name__ == "__main__":
    # Frontend Streamlit
    st.title("Lấy nội dung YouTube bằng tiếng Việt")
    
    # Create session state 
    if 'video_ids' not in st.session_state:
        st.session_state.video_ids = None
    if 'query' not in st.session_state:
        st.session_state.query = ""
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    
    with st.form("search_form"):
        query = st.text_input("Nhập từ khóa tìm kiếm hoặc tên kênh YouTube (bắt đầu bằng @):", 
                            placeholder="Ví dụ: 'việt tân' hoặc '@VietTan'",
                            value=st.session_state.query)
        max_results = st.slider("Số lượng video tối đa:", min_value=1, max_value=50, value=5)
        submit_button = st.form_submit_button("Tìm kiếm")
        
        if submit_button:
            st.session_state.query = query
            st.session_state.submitted = True
            # Reset video_ids when have new searching
            st.session_state.video_ids = None
    
    # If it is a new submission or a previous submission
    if submit_button or st.session_state.submitted:
        if st.session_state.video_ids is None:
            with st.spinner(f"Đang tìm kiếm video cho '{query}'..."):
                video_ids = get_video_ids_by_query(st.session_state.query, max_results, api_key=YOUTUBE_API_KEY)
                st.session_state.video_ids = video_ids
        
        if not st.session_state.video_ids:
            st.error("Không tìm thấy video nào cho truy vấn này.")
        else:
            # Show number of videos found
            st.success(f"Đã tìm thấy {len(st.session_state.video_ids)} video.")
            
            # Get current status
            results, all_completed = get_latest_status(st.session_state.video_ids)
            
            # Show status board
            status_df = pd.DataFrame(
                [(r[0], r[1], r[2]) for r in results], 
                columns=["Video ID", "URL", "Trạng thái"]
            )
            st.subheader("Trạng thái xử lý video")
            st.dataframe(status_df)
            
            # If processing, show reload button
            pending_count = sum(1 for r in results if r[2] != TaskStatus.SUCCESS.value)
            if pending_count > 0:
                st.info(f"Đang xử lý {pending_count}/{len(results)} video. Tải lại trang để cập nhật trạng thái.")
                if st.button("Tải lại trạng thái"):
                    st.rerun()
                
                # Auto refresh evvery 10 giây
                with st.empty():
                    for i in range(10, 0, -1):
                        st.write(f"Tự động tải lại sau {i} giây...")
                        time.sleep(1)
                    st.rerun()
        
            if all_completed:
                st.success("Tất cả video đã được xử lý xong!")
                
                # Show details results
                full_df = pd.DataFrame(
                    [(r[0], r[1], r[3], r[4]) for r in results], 
                    columns=["ID", "URL", "Transcript", "Content"]
                )
                
                st.subheader("Kết quả cuối cùng")
                st.dataframe(full_df)
                
                # Download CSV button
                if st.button("Tải xuống dạng CSV"):
                    csv = full_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Tải xuống",
                        data=csv,
                        file_name=f"youtube_results_{st.session_state.query.replace(' ', '_')}.csv",
                        mime="text/csv",
                    )