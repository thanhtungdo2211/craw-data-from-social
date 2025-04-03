import yt_dlp as youtube_dlp
import os
import logging
    
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
