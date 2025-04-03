from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults
import logging

class YouTubeVideoSensor(BaseSensorOperator):
    """
    Sensor kiểm tra xem một ID video YouTube có hợp lệ không.
    """
    
    @apply_defaults
    def __init__(self, video_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.video_id = video_id
        
    def poke(self, context):
        import requests
        try:
            response = requests.get(f"https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v={self.video_id}")
            return response.status_code == 200
        except Exception as e:
            logging.error(f"Video ID {self.video_id} không hợp lệ: {str(e)}")
            return False