from airflow.decorators import task

import config

@task.virtualenv(
    requirements=[f"youtube_transcript_api=={config.YT_TRANSCRIPT_API_VERSION}"],
    system_site_packages=False,
)
def check_transcripts_and_split(transcript_dir: str, transcript_file: str, video_ids: list = None) -> list:
    """
    Check and classify videos based on Vietnamese transcripts.
    
    Args:
        transcript_dir (str): Directory to store transcripts
        transcript_file (str): Path to the output CSV file
        video_ids (list): List of video IDs from the previous task
        
    Returns:
        list: List of video IDs that need audio download
    """
    import logging
    import os
    import csv
    
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
    from youtube_transcript_api.formatters import TextFormatter
    
    os.makedirs(transcript_dir, exist_ok=True)
    
    formatter = TextFormatter()

    if not video_ids:
        logging.warning("No video IDs found")
        return []
    
    audio_list = []
    videos_with_transcript = 0

    # Create CSV file (open in append mode)
    with open(transcript_file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Write header if the file is empty
        if os.stat(transcript_file).st_size == 0:
            writer.writerow(["video_id", "video_link", "transcript"])

        for video_id in video_ids:
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                has_vi = any(t.language_code == 'vi' for t in transcript_list)
            except (TranscriptsDisabled, NoTranscriptFound) as e:
                logging.info(f"Video {video_id} has no transcript: {str(e)}")
                has_vi = False
            except Exception as e:
                logging.error(f"Error processing video {video_id}: {str(e)}")
                audio_list.append(str(video_id))  # Ensure it's a string
                continue

            if has_vi:
                try:
                    vi_transcript = transcript_list.find_transcript(['vi'])
                    transcript_data = vi_transcript.fetch()
                    text_formatter = formatter.format_transcript(transcript_data)
                    writer.writerow([video_id, f"https://www.youtube.com/watch?v={video_id}", text_formatter])
                    videos_with_transcript += 1
                except Exception as e:
                    logging.error(f"Error processing Vietnamese transcript for {video_id}: {str(e)}")
                    audio_list.append(str(video_id))
            else:
                audio_list.append(str(video_id))
    
    # Log results
    logging.info(f"Number of videos with Vietnamese transcripts: {videos_with_transcript}/{len(video_ids)}")
    logging.info(f"Number of videos requiring audio download: {len(audio_list)}")
    
    # Return the list for further processing (will automatically be pushed to XCom)
    return audio_list
