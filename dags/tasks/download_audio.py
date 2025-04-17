from airflow.decorators import task
import config  

@task.virtualenv(
    requirements=[f"yt-dlp=={config.YT_DLP_VERSION}"],
    system_site_packages=False,
)
def download_single_audio(video_id: str, output_dir: str, format_audio: str = "bestaudio/best", 
                          codec: str = "mp3", quality: str = "192") -> str:
    """
    Download audio for a single YouTube video.
    
    Args:
        video_id (str): YouTube video ID
        output_dir (str): Directory to save audio files
        format_audio (str): Format to download
        codec (str): Audio codec
        quality (str): Audio quality
        
    Returns:
        str: Status message
    """
    import yt_dlp as youtube_dlp
    import os
    import logging
    
    os.makedirs(output_dir, exist_ok=True)
    
    logging.info(f"Downloading audio for video {video_id} to {output_dir}")
    
    link = f'https://www.youtube.com/watch?v={video_id}'
    ydl_opts = {
        'format': format_audio,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': codec,
            'preferredquality': quality,
        }],
        'outtmpl': f'{output_dir}/%(id)s.%(ext)s',
        'quiet': True
    }
    
    try:
        with youtube_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
        return f"Successfully downloaded {video_id}"
    except Exception as e:
        logging.error(f"Failed to download {video_id}: {str(e)}")
        return f"Failed to download {video_id}: {str(e)}"

@task
def process_audio_list(audio_list: list = None) -> list:
    """
    Process list of videos that need audio download.
    
    Args:
        audio_list (list): List of video IDs to download audio for
        
    Returns:
        list: Processed list of video IDs
    """
    import logging
    
    if not audio_list:
        logging.info("No video IDs found for audio download")
        return []
    
    simple_list = [str(vid) for vid in audio_list if vid]
    logging.info(f"Processing {len(simple_list)} videos for audio download")
    return simple_list