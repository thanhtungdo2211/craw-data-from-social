"""
Configuration module for YouTube pipeline.
Contains all constants, paths, and default values.
"""
import os
from airflow.models import Variable

# Default search parameters
DEFAULT_MAX_RESULTS = Variable.get("YT_DEFAULT_MAX_RESULTS", default_var=50, deserialize_json=False)
# Thay đổi định nghĩa DEFAULT_KEYWORDS
try:
    # Truy cập Airflow Variable
    DEFAULT_KEYWORDS = Variable.get("YT_DEFAULT_KEYWORDS", deserialize_json=True)
except Exception:
    # Fallback nếu biến không tồn tại hoặc không thể deserialize
    DEFAULT_KEYWORDS = ["việt nam", "tin tức việt nam", "việt tân"]
    
# File paths
BASE_DATA_DIR = os.environ.get('DATA_DIR', '/opt/airflow/data')
TRANSCRIPT_DIR = os.path.join(BASE_DATA_DIR, 'transcripts')
AUDIO_DIR = os.path.join(BASE_DATA_DIR, 'audio')
TRANSCRIPT_FILE = os.path.join(TRANSCRIPT_DIR, "transcripts_output.csv")

# Task configurations
AUDIO_DOWNLOAD_FORMAT = 'bestaudio/best'
AUDIO_CODEC = 'mp3'
AUDIO_QUALITY = '192'

# API configurations - use Airflow Variables for sensitive information
YT_DLP_VERSION = "2025.3.27"
YT_TRANSCRIPT_API_VERSION = "1.0.3"

# Performance settings
# MAX_PARALLEL_DOWNLOADS = Variable.get("YT_MAX_PARALLEL_DOWNLOADS", default_var=5, deserialize_json=False)
# SEARCH_BATCH_SIZE = 50