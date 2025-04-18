import logging
import uuid
from sqlalchemy.exc import SQLAlchemyError

from database import get_db
from models import YouTubeVideo
from core.extract_content import extract_content_from_transcript
from worker.schema import TaskStatus

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_video_from_db(video_id):
    """Get data from database"""
    db = get_db()
    try:
        return db.query(YouTubeVideo).filter(YouTubeVideo.video_id == video_id).first()
    except SQLAlchemyError as e:
        logger.error(f"Error when query database: {str(e)}")
        return None
    finally:
        db.close()

def create_pending_video(video_id, url, task_id=None):
    """
    Create PENDING record in database while task assign
    
    Args:
        video_id (str): ID of video YouTube
        url (str): URL of video
        task_id (str): ID of Celery task
        
    Returns:
        str: task_id used
    """
    if task_id is None:
        task_id = str(uuid.uuid4())
    
    db = get_db()
    try:
        # Check if video is exist
        existing_video = db.query(YouTubeVideo).filter(YouTubeVideo.video_id == video_id).first()
        
        if existing_video:
            # If video is succesfull insert, do nothing
            if existing_video.status == TaskStatus.SUCCESS.value:
                return existing_video.task_id
                
            # If video is pending, update task_id
            existing_video.task_id = task_id
            existing_video.status = TaskStatus.PENDING.value
        else:
            # Create new record with status is PENDING
            new_video = YouTubeVideo(
                video_id=video_id,
                url=url,
                task_id=task_id,
                status=TaskStatus.PENDING.value
            )
            db.add(new_video)
            
        db.commit()
        return task_id
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error: {str(e)}")
        return None
    finally:
        db.close()

def update_video_status(video_id, status, transcript=None, content=None):
    """
    Update status of video in database
    
    Args:
        video_id (str): ID of video YouTube
        status (str): New sattus (từ TaskStatus)
        transcript (str, optional): Content of transcript 
        content (str, optional): Content when intergrate with LLM
        
    Returns:
        bool: True nếu thành công, False nếu thất bại
    """
    db = get_db()
    try:
        video = db.query(YouTubeVideo).filter(YouTubeVideo.video_id == video_id).first()
        if not video:
            logger.error(f"Not found video {video_id} in database")
            return False
            
        video.status = status
        
        if transcript is not None:
            video.transcript = transcript
            
        if content is not None:
            video.content = content
            
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error when update status in video: {str(e)}")
        return False
    finally:
        db.close()

def save_video_to_db(video_id, url, transcript, content=None, status=TaskStatus.SUCCESS.value):
    """
    Save/update information of video into database
    
    Args:
        video_id (str): ID of video YouTube
        url (str): URL of video
        transcript (str): Content of transcript
        content (str, optional): Content. If None, extract from transcript
        status (str, optional): Status of video (default is SUCCESS)
        
    Returns:
        bool: True if succesfull, False if failure
    """
    if content is None and transcript:
        content = extract_content_from_transcript(transcript)
    
    db = get_db()
    try:
        # Check existing video
        existing_video = db.query(YouTubeVideo).filter(YouTubeVideo.video_id == video_id).first()
        
        if existing_video:
            # Update if information is exist
            existing_video.transcript = transcript
            existing_video.content = content
            existing_video.status = status
        else:
            # Create new if not exist
            video = YouTubeVideo(
                video_id=video_id,
                url=url,
                transcript=transcript,
                content=content,
                status=status
            )
            db.add(video)
        
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error when insert to database: {str(e)}")
        return False
    finally:
        db.close()