import sys
sys.setrecursionlimit(2000) 

from datetime import datetime, timedelta
from airflow import DAG
from airflow.decorators import task

import config
from tasks.get_video_ids_by_keywords import get_video_ids_by_keywords
from tasks.get_transcript import check_transcripts_and_split
from tasks.download_audio import download_single_audio, process_audio_list

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

    # Task 2: Check and get transcripts
    audio_ids = check_transcripts_and_split(
        transcript_dir=config.TRANSCRIPT_DIR,
        transcript_file=config.TRANSCRIPT_FILE,
        video_ids=video_ids 
    )

    # Task 3: Process audio list
    processed_ids = process_audio_list(audio_list=audio_ids) 
    
    # Task 4: Download audio
    download_tasks = download_single_audio.partial(
        output_dir=config.AUDIO_DIR,
        format_audio=config.AUDIO_DOWNLOAD_FORMAT,
        codec=config.AUDIO_CODEC,
        quality=config.AUDIO_QUALITY
    ).expand(
        video_id=processed_ids
    )
