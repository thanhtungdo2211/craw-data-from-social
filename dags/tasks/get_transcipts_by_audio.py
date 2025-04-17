from airflow.decorators import task

@task.virtualenv(
    requirements=[
        'faster-whisper==0.1.2',
    ],
    system_site_packages=False,
)
def audio_to_transcript(audio_path):
    """
    Convert audio file to transcript using Faster Whisper.
    
    Args:
        audio_path (str): Path to audio file
        
    Returns:
        str: Transcribed text
    """
    import logging
    from faster_whisper import WhisperModel #type: ignore[import]

    logging.info(f"Processing audio file: {audio_path}")
    
    # Initialize model
    model_size = "large-v3"
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    # Transcribe audio
    segments, info = model.transcribe(audio_path, beam_size=5)

    logging.info(f"Detected language '{info.language}' with probability {info.language_probability}")

    # Combine transcript segments
    transcription = ""
    for segment in segments:
        text = segment.text.strip()
        transcription += text + " "

    return transcription.strip()