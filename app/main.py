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

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

def trigger_processing_for_videos(video_ids):
    """Send video to background processing if not processed yet"""
    processed_ids = []
    
    for video_id in video_ids:
        db_video = get_video_from_db(video_id)
        if not db_video or db_video.status not in [TaskStatus.SUCCESS.value, TaskStatus.PROCESSING.value]:
            # Only process if not in DB or status is not SUCCESS/PROCESSING
            process_video(video_id)
            processed_ids.append(video_id)
    
    return processed_ids

@st.cache_data(ttl=1, max_entries=1, show_spinner=False)
def get_all_videos_cached(refresh_counter=0):
    """Get all videos from database with cache busting"""
    db = get_db()
    try:
        logger.info(f"Fetching fresh data from database, counter: {refresh_counter}")
        video_list = db.query(YouTubeVideo).order_by(YouTubeVideo.updated_at.desc()).limit(100).all()
        return video_list
    except SQLAlchemyError as e:
        logger.error(f"Error when query database: {str(e)}")
        return []
    finally:
        db.close()

def truncate_text(text, max_length=100):
    # if not text:
    #     return ""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

if __name__ == "__main__":
    # Frontend Streamlit
    st.title("Phát hiện nội dung vi phạm luật an ninh mạng trên Mạng xã hội")

    # Create session state 
    if 'video_ids' not in st.session_state:
        st.session_state.video_ids = None
    if 'query' not in st.session_state:
        st.session_state.query = ""
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    if 'processed_ids' not in st.session_state:
        st.session_state.processed_ids = set()
    if 'refresh_counter' not in st.session_state:
        st.session_state.refresh_counter = 0
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False
    if 'max_duration' not in st.session_state:
        st.session_state.max_duration = 600  

    # Form searching
    with st.form("search_form"):
        query = st.text_input("Nhập từ khóa tìm kiếm hoặc tên kênh YouTube (bắt đầu bằng @):", 
                            placeholder="Ví dụ: 'việt tân' hoặc '@VietTan'",
                            value=st.session_state.query)
        col1, col2 = st.columns(2)
        with col1:
            max_results = st.slider("Số lượng video tối đa:", min_value=1, max_value=50, value=5)
        with col2:
            max_duration = st.slider("Giới hạn độ dài video (giây):", 
                                min_value=30, max_value=600, value=st.session_state.max_duration,
                                help="Chỉ tìm những video có độ dài nhỏ hơn hoặc bằng giá trị này")
        
        submit_button = st.form_submit_button("Tìm kiếm")
        
        if submit_button:
            st.session_state.query = query
            st.session_state.max_duration = max_duration
            st.session_state.submitted = True
            st.session_state.video_ids = None
            st.session_state.processed_ids = set()

    if submit_button or (st.session_state.submitted and st.session_state.video_ids is None):
        with st.spinner(f"Đang tìm kiếm video cho '{st.session_state.query}'..."):
            video_ids = get_video_ids_by_query(st.session_state.query, max_results, 
                                            api_key=YOUTUBE_API_KEY, 
                                            max_duration=st.session_state.max_duration)
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
                    st.session_state.refresh_counter += 1

    st.subheader("Danh sách tất cả video")

    # Get the latest video data from the database
    all_videos = get_all_videos_cached(refresh_counter=st.session_state.refresh_counter)

    if not all_videos:
        st.info("Chưa có video nào được xử lý trong hệ thống.")
        # Stop auto refresh if there are no videos
        st.session_state.auto_refresh = False
    else:
        # Count number by status
        success_count = len([v for v in all_videos if v.status == TaskStatus.SUCCESS.value])
        failed_count = len([v for v in all_videos if v.status == TaskStatus.FAILURE.value])
        pending_count = len([v for v in all_videos if v.status in [TaskStatus.PENDING.value, TaskStatus.PROCESSING.value]])
        
        st.write(f"Tổng cộng: {len(all_videos)} video | "
                f"Thành công: {success_count} | "
                f"Thất bại: {failed_count} | "
                f"Đang xử lý: {pending_count}")
        
        # Check for videos that are processing
        pending_videos = [v for v in all_videos if v.status in [TaskStatus.PENDING.value, TaskStatus.PROCESSING.value]]
        
        # Manual refresh button before the table
        refresh_cols = st.columns([1, 3])
        with refresh_cols[0]:
            if pending_videos and st.button("Tải lại ngay", key="manual_refresh"):
                st.session_state.refresh_counter += 1
                # Turn off auto refresh before rerun to avoid ghost elements
                st.session_state.auto_refresh = False
                st.rerun()
        
        with refresh_cols[1]:
            if pending_videos:
                st.info(f"Đang xử lý {len(pending_videos)} video. Trang sẽ tự động cập nhật sau...")
                # Enable auto refresh if there are pending videos
                st.session_state.auto_refresh = True
        
        # Display data table
        all_data = []
        for video in all_videos:
            if video.status == TaskStatus.SUCCESS.value:
                transcript = truncate_text(video.transcript)
                content = truncate_text(video.content)
            elif video.status == TaskStatus.FAILURE.value:
                error_msg = video.transcript or video.content or "Không có thông tin lỗi"
                transcript = f"LỖI: {truncate_text(error_msg)}"
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
        
        # Display table with unique key
        st.dataframe(pd.DataFrame(all_data), use_container_width=True)
        
        # Export and retry failed videos
        if success_videos := [v for v in all_videos if v.status == TaskStatus.SUCCESS.value]:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Tải xuống dữ liệu thành công (CSV)", key="download_button"):
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
                        key="download_csv"
                    )
            
            # Retry failed videos
            if failed_videos := [v for v in all_videos if v.status == TaskStatus.FAILURE.value]:
                with col2:
                    if st.button("Thử lại xử lý các video lỗi", key="retry_button"):
                        retry_ids = [v.video_id for v in failed_videos]
                        processed = trigger_processing_for_videos(retry_ids)
                        st.session_state.processed_ids.update(processed)
                        if processed:
                            st.info(f"Đã gửi lại {len(processed)} video để xử lý.")
                            st.session_state.refresh_counter += 1
                            st.session_state.auto_refresh = True
                            st.rerun()

    # Countdown placed at the end, after everything is displayed
    # Ensure auto refresh only happens when pending_videos exists and auto_refresh=True
    if st.session_state.auto_refresh and 'pending_videos' in locals() and pending_videos:
        with st.empty():
            for i in range(10, 0, -1):
                st.write(f"Tự động tải lại sau {i} giây...")
                time.sleep(1)
                # Exit the loop if auto_refresh is turned off while counting
                if not st.session_state.auto_refresh:
                    break
            
            # Only rerun if auto_refresh is still on
            if st.session_state.auto_refresh:
                st.session_state.refresh_counter += 1
                st.rerun()
