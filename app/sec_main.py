import streamlit as st
import pandas as pd
import os
import logging

from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.formatters import TextFormatter

try:
    from core.get_video_ids_by_query import get_video_ids_by_query
    from core.download_audio import download_single_audio
    from core.speech2text import audio_to_transcript
except Exception as e:
    st.error(f"Eror when import module: {str(e)}")
    st.stop()

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

def process_video(video_id: str):
    """
    Extract one video to get transcript or audio.
    Args:
        video_id (str): YouTube video ID
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        has_vi = any(t.language_code == 'vi' for t in transcript_list)
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        logger.info(f"Video {video_id} không có transcript: {str(e)}")
        has_vi = False
    except Exception as e:
        logger.error(f"Lỗi khi xử lý video {video_id}: {str(e)}")
        return video_id, video_url, f"Lỗi: {str(e)}"

    if has_vi:
        try:
            formatter = TextFormatter()
            vi_transcript = transcript_list.find_transcript(['vi'])
            transcript_data = vi_transcript.fetch()
            text = formatter.format_transcript(transcript_data)
            return video_id, video_url, text
        except Exception as e:
            logger.error(f"Lỗi khi xử lý Vietnamese transcript cho {video_id}: {str(e)}")
            has_vi = False  # Chuyển sang phương pháp thay thế
    
    if not has_vi:
        audio_path = os.path.join(AUDIO_DIR, f"{video_id}.mp3")
        
        if not os.path.exists(audio_path):
            with st.spinner(f"Đang tải xuống audio cho video {video_id}..."):
                result = download_single_audio(
                    video_id=video_id,
                    output_dir=str(AUDIO_DIR),
                    format_audio="bestaudio/best",
                    codec="mp3",
                    quality="192"
                )
            
            if "Failed" in result:
                return video_id, video_url, "Không thể tải xuống audio"
        
        if os.path.exists(audio_path):
            with st.spinner(f"Đang chuyển đổi audio thành văn bản cho video {video_id}..."):
                try:
                    text = audio_to_transcript(audio_path)
                    return video_id, video_url, text
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý speech-to-text cho {video_id}: {str(e)}")
                    return video_id, video_url, f"Lỗi STT: {str(e)}"
        else:
            return video_id, video_url, "Không tìm thấy file audio"
    
    return video_id, video_url, "Không thể lấy transcript"

if __name__ == "__main__":
    # Frontend Streamlit
    st.title("Lấy nội dung YouTube bằng tiếng Việt")

    with st.form("search_form"):
        query = st.text_input("Nhập từ khóa tìm kiếm hoặc tên kênh YouTube (bắt đầu bằng @):", 
                            placeholder="Ví dụ: 'việt tân' hoặc '@viettan'")
        max_results = st.slider("Số lượng video tối đa:", min_value=1, max_value=50, value=5)
        submitted = st.form_submit_button("Tìm kiếm")

    if submitted and query:
        with st.spinner(f"Đang tìm kiếm video cho '{query}'..."):
            video_ids = get_video_ids_by_query(query, max_results, api_key=YOUTUBE_API_KEY)
        
        if not video_ids:
            st.error("Không tìm thấy video nào cho truy vấn này.")
        else:
            st.success(f"Đã tìm thấy {len(video_ids)} video.")
            
            df = pd.DataFrame(columns=["ID", "URL", "Transcript"])
            
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
            
            df = pd.DataFrame(results, columns=["ID", "URL", "Transcript"])
            
            st.dataframe(df)
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Tải xuống dạng CSV",
                data=csv,
                file_name=f"youtube_results_{query.replace(' ', '_')}.csv",
                mime="text/csv",
            )