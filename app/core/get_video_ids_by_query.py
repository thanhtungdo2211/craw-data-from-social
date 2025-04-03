import logging
import yt_dlp as youtube_dlp #type: ignore
import os
from typing import List
import googleapiclient.discovery

def get_video_ids_by_query(query: str, max_results: int, api_key: str = None) -> list:
    """
    Retrieve YouTube video IDs based on a keyword or channel username.
    
    Args:
        query (str): Search keyword or channel username with @ prefix
        max_results (int): Maximum total results to retrieve
        api_key (str, optional): YouTube Data API key for channel searches
        
    Returns:
        list: List of YouTube video IDs
    """
    logging.info(f"Starting search with query: {query}, max_results: {max_results}")
    
    all_video_ids = []
    
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
            youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=api_key)
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
            
            # Add unique video IDs from channel
            for video_id in channel_videos:
                if video_id not in all_video_ids:
                    all_video_ids.append(video_id)
                    if len(all_video_ids) >= max_results:
                        break
            
        else:
            # Regular keyword search using yt-dlp
            search_query = f"ytsearch{max_results}:{query}"
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
                            if video_id not in all_video_ids:
                                all_video_ids.append(video_id)
                                if len(all_video_ids) >= max_results:
                                    break
            
    except Exception as e:
        logging.error(f"Error processing query '{query}': {str(e)}")
        return []
    
    # Ensure we don't return more than requested
    all_video_ids = all_video_ids[:max_results]
    logging.info(f"Found {len(all_video_ids)} videos from query: {query}")
    
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