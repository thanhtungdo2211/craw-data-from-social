import logging
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

from database import get_db
from models import YouTubeVideo
from core.extract_content import extract_content_from_transcript

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv("./.env")

def get_video_from_db(video_id):
    """
    Lấy dữ liệu video từ database
    
    Args:
        video_id (str): ID của video YouTube
        
    Returns:
        YouTubeVideo or None: Đối tượng video nếu tìm thấy, None nếu không
    """
    db = get_db()
    try:
        return db.query(YouTubeVideo).filter(YouTubeVideo.video_id == video_id).first()
    except SQLAlchemyError as e:
        logger.error(f"Lỗi khi truy vấn database: {str(e)}")
        return None
    finally:
        db.close()

def save_video_to_db(video_id, url, transcript, content=None):
    """
    Lưu thông tin video vào database
    
    Args:
        video_id (str): ID của video YouTube
        url (str): URL đầy đủ của video
        transcript (str): Nội dung transcript
        content (str, optional): Nội dung đã xử lý. Nếu None, sẽ trích xuất từ transcript
        
    Returns:
        bool: True nếu lưu thành công, False nếu thất bại
    """
    if content is None and transcript:
        content = extract_content_from_transcript(transcript)
    
    db = get_db()
    try:
        # Kiểm tra video đã tồn tại chưa
        existing_video = db.query(YouTubeVideo).filter(YouTubeVideo.video_id == video_id).first()
        
        if existing_video:
            # Cập nhật nếu đã tồn tại
            existing_video.transcript = transcript
            existing_video.content = content
        else:
            # Tạo mới nếu chưa tồn tại
            video = YouTubeVideo(
                video_id=video_id,
                url=url,
                transcript=transcript,
                content=content
            )
            db.add(video)
        
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Lỗi khi lưu vào database: {str(e)}")
        return False
    finally:
        db.close()
