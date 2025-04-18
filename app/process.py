# [phần import các module cần thiết]
from worker.worker_process_video import process_video_task
from worker.schema import TaskStatus
from core.database_utils import get_video_from_db, create_pending_video

def process_video(video_id: str):
    """
    Create task to processing video and tracking progress
    
    Args:
        video_id (str): ID of YouTube video 
        
    Returns:
        tuple: (video_id, url, transcript, content)
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Check existing in database
    db_video = get_video_from_db(video_id)
    
    # If video is successfull, return information
    if db_video and db_video.status == TaskStatus.SUCCESS.value:
        return video_id, video_url, db_video.transcript, db_video.content
    
    # If the video is being processed or does not exist, create a new task
    task_id = create_pending_video(video_id, video_url)
    
    # Run background task
    process_video_task.delay(video_id)
    
    # Returns the current state
    if db_video:
        return video_id, video_url, f"Processing (status: {db_video.status})", "Processing..."
    else:
        return video_id, video_url, "Pending (PENDING)", "Pending..."
