import os
import sys
import time
from pathlib import Path
import argparse
import logging

import sys
sys.path.insert(1, '.')
sys.path.insert(1, 'app/')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add current directory to sys.path
sys.path.insert(1, ".")

# Import required modules
from worker.worker_process_video import process_video_task, celery_process_video
from core.database_utils import get_video_from_db, create_pending_video
from worker.schema import TaskStatus

def monitor_task(video_id, timeout=1800, poll_interval=5):
    """
    Monitor the processing of a YouTube video.
    
    Args:
        video_id: YouTube video ID
        timeout: Total timeout duration in seconds
        poll_interval: Polling interval in seconds
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    logger.info(f"Started monitoring video processing: {video_url}")

    # Check if the video already exists in the database
    db_video = get_video_from_db(video_id)
    
    if db_video and db_video.status == TaskStatus.SUCCESS.value:
        logger.info(f"Video was already successfully processed: {video_id}")
        logger.info(f"Content: {db_video.content[:100]}...")
        return True
    
    # Create a new task if the video is not in the database
    if not db_video:
        logger.info(f"Creating a new task for video {video_id}")
        create_pending_video(video_id, video_url)
        
    # Submit a new task
    task = process_video_task.delay(video_id)
    task_id = task.id
    logger.info(f"Submitted new task with ID: {task_id}")
    
    # Monitor the task progress
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check task status from Celery
        task_result = celery_process_video.AsyncResult(task_id)
        task_status = task_result.status
        
        # Check status in the database
        db_video = get_video_from_db(video_id)
        db_status = db_video.status if db_video else "UNKNOWN"
        
        logger.info(f"Status - Celery: {task_status}, Database: {db_status}")
        
        if task_status == 'SUCCESS' or db_status == TaskStatus.SUCCESS.value:
            logger.info("✅ Task completed successfully!")
            if db_video and db_video.transcript:
                logger.info(f"Transcript length: {len(db_video.transcript)}")
                logger.info(f"Content: {db_video.content[:100]}..." if db_video.content else "No content")
            return True
            
        if task_status == 'FAILURE' or db_status == TaskStatus.FAILURE.value:
            error_msg = db_video.transcript if db_video else "Unknown error"
            logger.error(f"❌ Task failed: {error_msg}")
            return False
            
        # Wait and check again
        time.sleep(poll_interval)
        
    logger.error(f"⏱️ Timeout after {timeout} seconds")
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test YouTube video processing")
    parser.add_argument("video_id", help="YouTube video ID", default="Zai0Qh5VNts")
    parser.add_argument("--timeout", type=int, default=1800, help="Timeout in seconds (default: 1800)")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds (default: 5)")
    
    args = parser.parse_args()
    
    success = monitor_task(args.video_id, args.timeout, args.interval)
    if success:
        logger.info("Test completed successfully!")
    else:
        logger.error("Test failed!")
