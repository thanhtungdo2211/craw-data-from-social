import yt_dlp
import json

max_duration = 100

def get_audio_duration(video_id):
    link = f'https://www.youtube.com/watch?v={video_id}'
    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'skip_download': True,  # Không tải file về
        'dump_single_json': True  # Lấy thông tin dưới dạng JSON
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=False)
        duration = info.get('duration')  # Thời lượng tính bằng giây
        
    return duration  # Trả về số giây

