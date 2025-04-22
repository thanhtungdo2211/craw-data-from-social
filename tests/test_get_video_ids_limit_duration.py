import logging
import yt_dlp as youtube_dlp #type: ignore
import os
from typing import List
import googleapiclient.discovery
from dotenv import load_dotenv

import sys
sys.path.insert(1, '.')
sys.path.insert(1, 'app/')
from core.download_audio import get_audio_duration  # Thêm import này

def get_video_ids_by_query(query: str, max_results: int, api_key: str = None, max_duration: float = None) -> list:
    """
    Retrieve YouTube video IDs based on a keyword or channel username.
    
    Args:
        query (str): Search keyword or channel username with @ prefix
        max_results (int): Maximum total results to retrieve
        api_key (str, optional): YouTube Data API key for channel searches
        max_duration (float, optional): Maximum duration of videos in seconds
        
    Returns:
        list: List of YouTube video IDs
    """
    logging.info(f"Starting search with query: {query}, max_results: {max_results}, max_duration: {max_duration}")
    
    all_video_ids = []
    processed_count = 0  # Số video đã xử lý (kể cả bị loại)
    
    try:
        if query.startswith('@'):
            # This is a channel username
            channel_username = query[1:]  # Remove '@'
            logging.info(f"Searching videos from channel: {channel_username}")
            
            # Get API key from environment if not provided
            if not api_key:
                api_key = os.environ.get('YOUTUBE_API_KEY')
                if not api_key:
                    raise ValueError("API key required for channel search but not provided")
            
            # Get channel ID from username
            youtube = googleapiclient.discovery.build(
                'youtube', 'v3', 
                developerKey=api_key,
                cache_discovery=True
            )
            search_response = youtube.search().list(
                part='id',
                q=channel_username,
                type='channel',
                maxResults=1
            ).execute()
            
            if not search_response.get('items'):
                logging.warning(f"Channel not found for username: {channel_username}")
                return []
                
            channel_id = search_response['items'][0]['id']['channelId']
            logging.info(f"Found channel ID: {channel_id} for username: {channel_username}")
            
            # Get videos from channel
            channel_videos = get_video_ids_by_channel(channel_id, api_key)
            
            # Add unique video IDs from channel with duration check
            for video_id in channel_videos:
                if processed_count >= max_results * 3:  # Limit total processed to avoid too much time
                    break
                    
                processed_count += 1
                
                # Kiểm tra độ dài nếu max_duration được chỉ định
                if max_duration is not None:
                    try:
                        duration = get_audio_duration(video_id)
                        if duration is None or duration > max_duration:
                            logging.info(f"Skipping video {video_id}: Duration {duration}s exceeds limit {max_duration}s")
                            continue
                    except Exception as e:
                        logging.warning(f"Could not check duration for {video_id}: {e}")
                        continue
                
                if video_id not in all_video_ids:
                    all_video_ids.append(video_id)
                    if len(all_video_ids) >= max_results:
                        break
            
        else:
            # Regular keyword search using yt-dlp
            # Tăng số lượng kết quả tìm kiếm để có đủ video sau khi lọc
            search_multiplier = 3 if max_duration else 1
            search_query = f"ytsearch{max_results * search_multiplier}:{query}"
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'force_generic_extractor': True,
                'ignoreerrors': True,
            }
            
            with youtube_dlp.YoutubeDL(ydl_opts) as ydl:
                results = ydl.extract_info(search_query, download=False)
                if 'entries' in results:
                    for entry in results['entries']:
                        if entry and 'id' in entry:
                            video_id = entry['id']
                            processed_count += 1
                            
                            # Kiểm tra độ dài nếu max_duration được chỉ định
                            if max_duration is not None:
                                try:
                                    duration = get_audio_duration(video_id)
                                    if duration is None or duration > max_duration:
                                        logging.info(f"Skipping video {video_id}: Duration {duration}s exceeds limit {max_duration}s")
                                        continue
                                except Exception as e:
                                    logging.warning(f"Could not check duration for {video_id}: {e}")
                                    continue
                            
                            if video_id not in all_video_ids:
                                all_video_ids.append(video_id)
                                if len(all_video_ids) >= max_results:
                                    break
            
    except Exception as e:
        logging.error(f"Error processing query '{query}': {str(e)}")
        return []
    
    # Ensure we don't return more than requested
    all_video_ids = all_video_ids[:max_results]
    logging.info(f"Found {len(all_video_ids)} videos matching criteria from query: {query}")
    logging.info(f"Processed {processed_count} videos in total during search")
    
    return all_video_ids

def get_video_ids_by_channel(channel_id: str, api_key: str = None) -> List[str]:
    """
    Retrieve all video IDs from a YouTube channel.
    
    Args:
        channel_id (str): The YouTube channel ID.
        api_key (str, optional): YouTube Data API key. If None, looks for YOUTUBE_API_KEY environment variable.
    
    Returns:
        List[str]: A list of video IDs from the channel.
    """
    # Get API key from environment variable if not provided
    if not api_key:
        api_key = os.environ.get('YOUTUBE_API_KEY')
        if not api_key:
            raise ValueError("API key not provided and YOUTUBE_API_KEY environment variable not set")
    
    # Initialize YouTube API client
    youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=api_key)
    
    # First, get the channel's uploads playlist ID
    channel_response = youtube.channels().list(
        part='contentDetails',
        id=channel_id
    ).execute()
    
    if not channel_response.get('items'):
        raise ValueError(f"Channel with ID {channel_id} not found")
    
    uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    # Now get all videos from the uploads playlist
    video_ids = []
    next_page_token = None
    
    while True:
        playlist_response = youtube.playlistItems().list(
            part='contentDetails',
            playlistId=uploads_playlist_id,
            maxResults=50,  # Maximum allowed by the API
            pageToken=next_page_token
        ).execute()
        
        for item in playlist_response.get('items', []):
            video_ids.append(item['contentDetails']['videoId'])
        
        next_page_token = playlist_response.get('nextPageToken')
        if not next_page_token:
            break
    
    return video_ids

if __name__ == "__main__":

    load_dotenv('./.env')
    api_key = os.getenv('YOUTUBE_API_KEY')


    # Thông số tìm kiếm
    channel_query = "vạn thịnh phát"
    max_results = 10
    max_duration = 600  # Giới hạn video 10 phút (600 giây)
    
    # Tìm kiếm video từ channel
    print(f"Đang tìm kiếm video từ channel {channel_query}...")
    video_ids = get_video_ids_by_query(
        query=channel_query, 
        max_results=max_results,
        api_key=api_key,
        max_duration=max_duration
    )
    
    # In kết quả
    print(f"\nĐã tìm thấy {len(video_ids)} video từ {channel_query}:")
    for i, video_id in enumerate(video_ids, 1):
        try:
            duration = get_audio_duration(video_id)
            print(f"{i}. Video ID: {video_id} - Duration: {duration:.2f} seconds")
            print(f"   URL: https://www.youtube.com/watch?v={video_id}")
        except Exception as e:
            print(f"{i}. Video ID: {video_id} - Không thể lấy được thông tin duration: {str(e)}")
    
    print(f"\nQuá trình tìm kiếm hoàn tất.")
