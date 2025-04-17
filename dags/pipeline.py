import sys
sys.setrecursionlimit(2000) 

from datetime import datetime, timedelta
from airflow import DAG
from airflow.decorators import task

import config
from tasks.get_video_ids_by_keywords import get_video_ids_by_keywords
from tasks.get_transcript import check_transcripts_and_split_db_with_hook
from tasks.download_audio import download_single_audio, process_audio_list
from tasks.get_transcipts_by_audio import audio_to_transcript

# Task to save speech-to-text transcripts to database
@task
def save_audio_transcript_to_db(video_id: str, transcript: str):
    """
    Save transcript from speech-to-text to database.
    
    Args:
        video_id (str): YouTube video ID
        transcript (str): Transcript text from speech-to-text
    """
    import logging
    from airflow.providers.postgres.hooks.postgres import PostgresHook
    
    if not transcript:
        logging.warning(f"Empty transcript for video {video_id}")
        return
    
    # Connect to database
    hook = PostgresHook(postgres_conn_id="postgres_default")
    
    # Insert or update transcript in database
    upsert_sql = """
    INSERT INTO youtube_videos (video_id, url, transcript)
    VALUES (%s, %s, %s)
    ON CONFLICT (video_id)
    DO UPDATE SET 
        transcript = EXCLUDED.transcript;
    """
    
    try:
        hook.run(
            upsert_sql,
            parameters=(video_id, f"https://www.youtube.com/watch?v={video_id}", transcript)
        )
        logging.info(f"Successfully saved STT transcript for {video_id}")
    except Exception as e:
        logging.error(f"Failed to save STT transcript for {video_id}: {str(e)}")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'start_date': datetime.now(),
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='youtube_pipeline_dag',
    default_args=default_args,
    description='Extract Vietnamese transcripts from YouTube videos',
    schedule_interval=None,
    catchup=False,
    tags=['youtube', 'transcript', 'audio'],
    max_active_runs=1
) as dag: 
    # Task 1: Get video IDs
    video_ids = get_video_ids_by_keywords(
        keywords=config.DEFAULT_KEYWORDS,
        max_results=int(config.DEFAULT_MAX_RESULTS)
    )

    # Task 2: Check transcripts and save to DB, return videos without transcripts
    audio_ids = check_transcripts_and_split_db_with_hook(
        video_ids=video_ids 
    )

    # Task 3: Process audio list for videos without transcripts
    processed_ids = process_audio_list(audio_list=audio_ids) 
    
    # Task 4: Download audio for videos without transcripts
    download_tasks = download_single_audio.partial(
        output_dir=config.AUDIO_DIR,
        format_audio=config.AUDIO_DOWNLOAD_FORMAT,
        codec=config.AUDIO_CODEC,
        quality=config.AUDIO_QUALITY
    ).expand(
        video_id=processed_ids
    )
    
    # Task 5: Generate audio paths for STT processing
    @task
    def build_audio_paths(video_ids):
        """
        Build paths to downloaded audio files
        
        Args:
            video_ids (list): List of video IDs
            
        Returns:
            list: List of (video_id, audio_path) tuples
        """
        import os
        paths = []
        for vid in video_ids:
            audio_path = os.path.join(config.AUDIO_DIR, f"{vid}.mp3")
            paths.append((vid, audio_path))
        return paths
    
    # Create audio paths
    audio_paths = build_audio_paths(processed_ids)
    
    # Task 6: Run speech-to-text on downloaded audio
    transcripts = audio_to_transcript.partial().expand(
        audio_path=[p[1] for p in audio_paths]
    )
    
    # Task 7: Save speech-to-text transcripts to database
    store_transcripts = save_audio_transcript_to_db.partial().expand(
        video_id=[p[0] for p in audio_paths],
        transcript=transcripts
    )
    
    # Set task dependencies
    video_ids >> audio_ids >> processed_ids >> download_tasks
    download_tasks >> audio_paths >> transcripts >> store_transcripts