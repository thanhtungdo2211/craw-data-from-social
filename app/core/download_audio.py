import yt_dlp as youtube_dlp
import os
import logging

def get_audio_duration(video_id):
    link = f'https://www.youtube.com/watch?v={video_id}'
    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'skip_download': True,  # Không tải file về
        'dump_single_json': True  # Lấy thông tin dưới dạng JSON
    }
    
    with youtube_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=False)
        duration = info.get('duration')  # Thời lượng tính bằng giây
        
    return duration  # Trả về số giây

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
