from airflow.decorators import task

import config

@task.virtualenv(
    requirements=[f"youtube_transcript_api=={config.YT_TRANSCRIPT_API_VERSION}"],
    system_site_packages=False,
)
def check_transcripts_and_split_db_with_hook(video_ids: list = None) -> list:
    """
    Check and classify videos based on Vietnamese transcripts, then save transcripts to DB (Postgres)
    using PostgresHook (no SQLAlchemy). Returns a list of video IDs that need audio download.
    
    Args:
        video_ids (list): List of YouTube video IDs to process
        
    Returns:
        list: List of video IDs without Vietnamese transcripts (need audio download)
    """
    import logging
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
    from youtube_transcript_api.formatters import TextFormatter
    from airflow.providers.postgres.hooks.postgres import PostgresHook

    if not video_ids:
        logging.warning("No video IDs found")
        return []

    # Airflow PostgresHook
    hook = PostgresHook(postgres_conn_id="postgres_default")

    formatter = TextFormatter()
    audio_list = []
    videos_with_transcript = 0

    for video_id in video_ids:
        try:
            # Try to get transcript list for video
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            has_vi = any(t.language_code == 'vi' for t in transcript_list)
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            logging.info(f"Video {video_id} has no transcript: {str(e)}")
            has_vi = False
        except Exception as e:
            logging.error(f"Error processing video {video_id}: {str(e)}")
            audio_list.append(str(video_id))
            continue

        # If video has Vietnamese transcript
        if has_vi:
            try:
                vi_transcript = transcript_list.find_transcript(['vi'])
                transcript_data = vi_transcript.fetch()
                text_formatter = formatter.format_transcript(transcript_data)

                # Insert into database with UPSERT
                upsert_sql = """
                INSERT INTO youtube_videos (video_id, url, transcript)
                VALUES (%s, %s, %s)
                ON CONFLICT (video_id)
                DO UPDATE SET 
                    transcript = EXCLUDED.transcript;
                """

                hook.run(
                    upsert_sql,
                    parameters=(video_id, f"https://www.youtube.com/watch?v={video_id}", text_formatter)
                )

                videos_with_transcript += 1

            except Exception as e:
                logging.error(f"Error processing Vietnamese transcript for {video_id}: {str(e)}")
                audio_list.append(str(video_id))
        else:
            # If no Vietnamese transcript, add to list for audio download
            audio_list.append(str(video_id))

    logging.info(f"Number of videos with Vietnamese transcripts: {videos_with_transcript}/{len(video_ids)}")
    logging.info(f"Number of videos requiring audio download: {len(audio_list)}")

    return audio_list