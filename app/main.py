import os
import logging
import time
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from core.get_video_ids_by_query import get_video_ids_by_query
from process import process_video
from core.database_utils import get_video_from_db
from database import get_db
from worker.schema import TaskStatus
from models import YouTubeVideo

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

def trigger_processing_for_videos(video_ids):
    """Gửi video tới xử lý background nếu chưa được xử lý"""
    processed_ids = []
    
    for video_id in video_ids:
        db_video = get_video_from_db(video_id)
        if not db_video or db_video.status not in [TaskStatus.SUCCESS.value, TaskStatus.PROCESSING.value]:
            # Chỉ xử lý nếu không có trong DB hoặc trạng thái không phải SUCCESS/PROCESSING
            process_video(video_id)
            processed_ids.append(video_id)
    
    return processed_ids

def get_all_videos(limit=100):
    db = get_db()
    try:
        video_list = db.query(YouTubeVideo).order_by(YouTubeVideo.updated_at.desc()).limit(limit).all()
        return video_list
    except SQLAlchemyError as e:
        logger.error(f"Error when query database: {str(e)}")
        return []
    finally:
        db.close()

def truncate_text(text, max_length=1000000):
    """Cắt ngắn văn bản nếu quá dài"""
    if not text:
        return ""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

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
    if 'processed_ids' not in st.session_state:
        st.session_state.processed_ids = set()
    
    # Form tìm kiếm
    with st.form("search_form"):
        query = st.text_input("Nhập từ khóa tìm kiếm hoặc tên kênh YouTube (bắt đầu bằng @):", 
                            placeholder="Ví dụ: 'việt tân' hoặc '@VietTan'",
                            value=st.session_state.query)
        max_results = st.slider("Số lượng video tối đa:", min_value=1, max_value=50, value=5)
        submit_button = st.form_submit_button("Tìm kiếm")
        
        if submit_button:
            st.session_state.query = query
            st.session_state.submitted = True
            st.session_state.video_ids = None
            st.session_state.processed_ids = set()
    
    if submit_button or (st.session_state.submitted and st.session_state.video_ids is None):
        with st.spinner(f"Đang tìm kiếm video cho '{st.session_state.query}'..."):
            video_ids = get_video_ids_by_query(st.session_state.query, max_results, api_key=YOUTUBE_API_KEY)
            st.session_state.video_ids = video_ids
        
        if not st.session_state.video_ids:
            st.error("Không tìm thấy video nào cho truy vấn này.")
        else:
            st.success(f"Đã tìm thấy {len(st.session_state.video_ids)} video cho '{st.session_state.query}'.")
            
            to_process = [v_id for v_id in st.session_state.video_ids 
                          if v_id not in st.session_state.processed_ids]
            
            if to_process:
                processed = trigger_processing_for_videos(to_process)
                st.session_state.processed_ids.update(processed)
                if processed:
                    st.info(f"Đã gửi {len(processed)} video để xử lý.")
    
    st.subheader("Danh sách tất cả video")
    
    all_videos = get_all_videos(limit=100)
    
    if not all_videos:
        st.info("Chưa có video nào được xử lý trong hệ thống.")
    else:
        # Hiển thị số lượng theo trạng thái
        success_count = len([v for v in all_videos if v.status == TaskStatus.SUCCESS.value])
        failed_count = len([v for v in all_videos if v.status == TaskStatus.FAILURE.value])
        pending_count = len([v for v in all_videos if v.status in [TaskStatus.PENDING.value, TaskStatus.PROCESSING.value]])
        
        st.write(f"Tổng cộng: {len(all_videos)} video | "
                 f"Thành công: {success_count} | "
                 f"Thất bại: {failed_count} | "
                 f"Đang xử lý: {pending_count}")
        
        # Tạo DataFrame hợp nhất từ tất cả các video
        all_data = []
        for video in all_videos:
            # Xác định nội dung hiển thị dựa trên trạng thái
            if video.status == TaskStatus.SUCCESS.value:
                transcript = truncate_text(video.transcript, 100)
                content = truncate_text(video.content, 100)
            elif video.status == TaskStatus.FAILURE.value:
                error_msg = video.transcript or video.content or "Không có thông tin lỗi"
                transcript = f"LỖI: {truncate_text(error_msg, 100)}"
                content = ""
            else:
                transcript = f"Đang xử lý... ({video.status})"
                content = "Đang xử lý..."
                
            all_data.append({
                "Video ID": video.video_id,
                "URL": video.url,
                "Trạng thái": video.status,
                "Cập nhật": video.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                "Transcript": transcript,
                "Content": content
            })
        
        # Hiển thị bảng hợp nhất
        unified_df = pd.DataFrame(all_data)
        st.dataframe(unified_df, use_container_width=True)
        
        # Button để tải xuống dữ liệu thành công
        success_videos = [v for v in all_videos if v.status == TaskStatus.SUCCESS.value]
        if success_videos:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Tải xuống dữ liệu thành công (CSV)"):
                    export_df = pd.DataFrame([{
                        "ID": v.video_id,
                        "URL": v.url,
                        "Transcript": v.transcript,
                        "Content": v.content,
                        "Thời gian xử lý": v.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                    } for v in success_videos])
                    
                    csv = export_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Tải xuống",
                        data=csv,
                        file_name=f"youtube_results_{time.strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                    )
            
            # Button để thử lại xử lý video lỗi
            failed_videos = [v for v in all_videos if v.status == TaskStatus.FAILURE.value]
            if failed_videos:
                with col2:
                    if st.button("Thử lại xử lý các video lỗi"):
                        retry_ids = [v.video_id for v in failed_videos]
                        processed = trigger_processing_for_videos(retry_ids)
                        st.session_state.processed_ids.update(processed)
                        if processed:
                            st.info(f"Đã gửi lại {len(processed)} video để xử lý.")
                            st.rerun()
        
        # Tự động làm mới nếu còn video đang xử lý
        pending_videos = [v for v in all_videos if v.status in [TaskStatus.PENDING.value, TaskStatus.PROCESSING.value]]
        if pending_videos:
            st.info(f"Đang xử lý {len(pending_videos)} video. Trang sẽ tự động cập nhật.")
            if st.button("Tải lại ngay"):
                st.rerun()
            
            # Auto refresh every 10 seconds
            st.write("Chờ tự động tải lại...")
            refresh_placeholder = st.empty()
            for i in range(10, 0, -1):
                refresh_placeholder.write(f"Tự động tải lại sau {i} giây...")
                time.sleep(1)
            st.rerun()