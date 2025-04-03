import os
from typing import List
import time
import unittest
from unittest.mock import patch, MagicMock

import googleapiclient.discovery #type: ignore[import]

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

class TestGetVideoIdsByChannel(unittest.TestCase):
    
    @patch('googleapiclient.discovery.build')
    def test_get_video_ids_by_channel(self, mock_build):
        # Mock the YouTube API responses
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube
        
        # Mock channel response
        mock_channel_response = {
            'items': [
                {
                    'contentDetails': {
                        'relatedPlaylists': {
                            'uploads': 'test_uploads_playlist_id'
                        }
                    }
                }
            ]
        }
        mock_youtube.channels().list().execute.return_value = mock_channel_response
        
        # Mock playlist response
        mock_playlist_response = {
            'items': [
                {'contentDetails': {'videoId': 'video1'}},
                {'contentDetails': {'videoId': 'video2'}},
                {'contentDetails': {'videoId': 'video3'}}
            ],
            'nextPageToken': None
        }
        mock_youtube.playlistItems().list().execute.return_value = mock_playlist_response
        
        # Call the function with a test channel ID
        with patch.dict(os.environ, {'YOUTUBE_API_KEY': 'test_api_key'}):
            result = get_video_ids_by_channel('test_channel_id')
        
        # Assert results
        self.assertEqual(len(result), 3)
        self.assertEqual(result, ['video1', 'video2', 'video3'])

if __name__ == '__main__':
    # unittest.main()
    API_KEY = "AIzaSyAksXQ8PeaFsqCsNo7CSuD9kJjT4xSEUQQ"
    channel_id = "UCJDyIKGZ9zpTKDTEXpivGZw"
    t1 = time.time()
    video_ids = get_video_ids_by_channel(channel_id, API_KEY)
    t2 = time.time()
    print(f"Time taken: {t2 - t1:.2f} seconds")
    print(f"Number of video IDs: {len(video_ids)}")
    with open("tests/video_ids.txt", "w") as f:
        for video_id in video_ids:
            f.write(f"{video_id}\n")
    print("Video IDs saved to video_ids.txt")
