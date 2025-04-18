import os
import sys
import logging
from pathlib import Path
import signal
import time
sys.path.insert(1, ".")

from celery import Celery
from celery.utils.log import get_task_logger
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.formatters import TextFormatter

# Import local modules
from config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND
from worker.worker_helper import is_backend_running, is_broker_running
from worker.schema import TaskStatus
from core.download_audio import download_single_audio
from core.speech2text import audio_to_transcript
from core.database_utils import update_video_status
from core.extract_content import extract_content_from_transcript

# Configure logging
logger = get_task_logger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

# Celery configuration
celery_process_video = Celery(
    "worker_process_video",
    backend=CELERY_RESULT_BACKEND,
    broker=CELERY_BROKER_URL
)
celery_process_video.conf.broker_connection_retry_on_startup = True

# Check connections
if not is_backend_running(logger=logger): exit()
if not is_broker_running(logger=logger): exit()

def timeout_handler(signum, frame):
    raise TimeoutError("Speech-to-text processing timed out")

@celery_process_video.task(
    bind=True,
    queue="process_video",
    name="process_video_task",
    acks_late=True, 
    max_retries=3, 
    time_limit=3600)  # Limit 1 hour
def process_video_task(self, video_id):
    """
    Background task to process YouTube video.
    
    Args:
        video_id (str): YouTube video ID
    
    Returns:
        dict: Result
    """
    task_id = self.request.id
    logger.info(f"Start processing video {video_id} with task_id {task_id}")
    
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Update status to PROCESSING
    update_video_status(video_id, TaskStatus.PROCESSING.value)
    
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        has_vi = any(t.language_code == 'vi' for t in transcript_list)
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        logger.info(f"Video {video_id} has no transcript: {str(e)}")
        has_vi = False
    except Exception as e:
        logger.error(f"Error while processing video {video_id}: {str(e)}")
        error_msg = f"Error: {str(e)}"
        update_video_status(video_id, TaskStatus.FAILURE.value, error_msg, error_msg)
        return {"status": "error", "message": error_msg}

    transcript_text = None
    
    if has_vi:
        try:
            formatter = TextFormatter()
            vi_transcript = transcript_list.find_transcript(['vi'])
            transcript_data = vi_transcript.fetch()
            transcript_text = formatter.format_transcript(transcript_data)
        except Exception as e:
            logger.error(f"Error processing Vietnamese transcript for {video_id}: {str(e)}")
            has_vi = False  
    
    if not has_vi or not transcript_text:
        audio_path = os.path.join(AUDIO_DIR, f"{video_id}.mp3")
        
        if not os.path.exists(audio_path):
            logger.info(f"Downloading audio for video {video_id}...")
            result = download_single_audio(
                video_id=video_id,
                output_dir=str(AUDIO_DIR),
                format_audio="bestaudio/best",
                codec="mp3",
                quality="192"
            )
            
            if "Failed" in result:
                error_msg = "Failed to download audio"
                update_video_status(video_id, TaskStatus.FAILURE.value, error_msg, error_msg)
                return {"status": "error", "message": error_msg}
        
        if os.path.exists(audio_path):
            logger.info(f"Converting audio to transcript for video {video_id}...")
            try:
                # Set timeout 10 minutes for speech-to-text
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(600)  # 600 seconds = 10 minutes
                
                start_time = time.time()
                self.update_state(state="PROGRESS", meta={"step": "speech_to_text_started"})
                
                transcript_text = audio_to_transcript(audio_path)
                
                # Cancel timeout
                signal.alarm(0)
                
                processing_time = time.time() - start_time
                logger.info(f"Finished STT in {processing_time:.2f}s")
                logger.info(f"Transcript: {transcript_text[:100]}...")
                
            except TimeoutError as e:
                logger.error(f"Speech-to-text processing timed out: {str(e)}")
                error_msg = "Timeout: STT took more than 10 minutes"
                update_video_status(video_id, TaskStatus.FAILURE.value, error_msg, error_msg)
                return {"status": "error", "message": error_msg}
            except Exception as e:
                logger.error(f"Error during speech-to-text for {video_id}: {str(e)}")
                error_msg = f"STT Error: {str(e)}"
                update_video_status(video_id, TaskStatus.FAILURE.value, error_msg, error_msg)
                return {"status": "error", "message": error_msg}
    
    if not transcript_text:
        error_msg = "Transcript not available"
        update_video_status(video_id, TaskStatus.FAILURE.value, error_msg, error_msg)
        return {"status": "error", "message": error_msg}
    
    # Extract content from transcript
    content = extract_content_from_transcript(transcript_text)
    
    # Update database with SUCCESS status
    update_video_status(video_id, TaskStatus.SUCCESS.value, transcript_text, content)
    
    return {
        "status": "success",
        "video_id": video_id,
        "url": video_url,
        "content_length": len(content) if content else 0,
        "transcript_length": len(transcript_text) if transcript_text else 0
    }
