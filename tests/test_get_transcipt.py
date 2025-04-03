from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.formatters import TextFormatter
import logging
import yt_dlp as youtube_dlp

import logging

formatter = TextFormatter()

video_id = "z9mwsrfSeuc" # PbrrXXmPC1Y
output_dir = "/mnt/d/Personal/Programing/Work/crawl-data-from-social/data/audio"

try:
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    has_vi = any(t.language_code == 'vi' for t in transcript_list)
except (TranscriptsDisabled, NoTranscriptFound) as e:
    logging.info(f"Video {video_id} has no transcript: {str(e)}")
    has_vi = False

if has_vi:
    try:
        vi_transcript = transcript_list.find_transcript(['vi'])
        transcript_data = vi_transcript.fetch()
        text_formatter = formatter.format_transcript(transcript_data)

    except Exception as e:
        logging.error(f"Error processing Vietnamese transcript for {video_id}: {str(e)}")
else:     
    link = f'https://www.youtube.com/watch?v={video_id}'
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'{output_dir}/%(id)s.%(ext)s',
        'quiet': True
    }
    try:
        with youtube_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
    except Exception as e:
        logging.error(f"Failed to download {video_id}: {str(e)}")

