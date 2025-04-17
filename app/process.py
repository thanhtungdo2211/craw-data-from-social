import os
import logging
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.formatters import TextFormatter

from core.download_audio import download_single_audio
from core.speech2text import audio_to_transcript
from core.database_utils import get_video_from_db, save_video_to_db
from core.extract_content import extract_content_from_transcript

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv("./.env")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "AIzaSyAksXQ8PeaFsqCsNo7CSuD9kJjT4xSEUQQ")

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

def process_video(video_id: str):
    """
    Extract one video to get transcript or audio.
    Args:
        video_id (str): YouTube video ID
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Kiểm tra trong database trước
    db_video = get_video_from_db(video_id)
    if db_video:
        logger.info(f"Đã tìm thấy video {video_id} trong database")
        return video_id, video_url, db_video.transcript, db_video.content
    
    # Nếu không có trong DB, tiến hành xử lý và lưu
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        has_vi = any(t.language_code == 'vi' for t in transcript_list)
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        logger.info(f"Video {video_id} không có transcript: {str(e)}")
        has_vi = False
    except Exception as e:
        logger.error(f"Lỗi khi xử lý video {video_id}: {str(e)}")
        error_msg = f"Lỗi: {str(e)}"
        save_video_to_db(video_id, video_url, error_msg, error_msg)
        return video_id, video_url, error_msg, error_msg

    transcript_text = None
    
    if has_vi:
        try:
            formatter = TextFormatter()
            vi_transcript = transcript_list.find_transcript(['vi'])
            transcript_data = vi_transcript.fetch()
            transcript_text = formatter.format_transcript(transcript_data)
        except Exception as e:
            logger.error(f"Lỗi khi xử lý Vietnamese transcript cho {video_id}: {str(e)}")
            has_vi = False  # Chuyển sang phương pháp thay thế
    
    if not has_vi or not transcript_text:
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
                error_msg = "Không thể tải xuống audio"
                save_video_to_db(video_id, video_url, error_msg, error_msg)
                return video_id, video_url, error_msg, error_msg
        
        if os.path.exists(audio_path):
            with st.spinner(f"Đang chuyển đổi audio thành văn bản cho video {video_id}..."):
                try:
                    transcript_text = audio_to_transcript(audio_path)
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý speech-to-text cho {video_id}: {str(e)}")
                    error_msg = f"Lỗi STT: {str(e)}"
                    save_video_to_db(video_id, video_url, error_msg, error_msg)
                    return video_id, video_url, error_msg, error_msg
        else:
            error_msg = "Không tìm thấy file audio"
            save_video_to_db(video_id, video_url, error_msg, error_msg)
            return video_id, video_url, error_msg, error_msg
    
    if not transcript_text:
        error_msg = "Không thể lấy transcript"
        save_video_to_db(video_id, video_url, error_msg, error_msg)
        return video_id, video_url, error_msg, error_msg
    
    # Trích xuất content từ transcript
    content = extract_content_from_transcript(transcript_text)
    
    # Lưu vào database
    save_video_to_db(video_id, video_url, transcript_text, content)
    
    return video_id, video_url, transcript_text, content