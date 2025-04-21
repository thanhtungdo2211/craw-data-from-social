import logging
import time
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

def audio_to_transcript(audio_path):
    """Convert audio to transcript using Whisper model"""
    start_time = time.time()

    # Log the start of the process
    logger.info(f"Starting Whisper model initialization for file {audio_path}")
    
    ###
    # Initialize a lighter model
    model_size = "small"  

    start_time = time.time()

    # Initialize the model inside the function instead of globally
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    logger.info(f"Model initialized in {time.time() - start_time:.2f}s")
    
    # Start transcribing
    logger.info("Starting transcription of the audio...")
    transcribe_start = time.time()
    segments, info = model.transcribe(audio_path, beam_size=5)
    
    logger.info(f"Detected language: {info.language} (confidence: {info.language_probability:.2f})")
    
    # Process each transcript segment
    transcription = ""
    for i, segment in enumerate(segments):
        if i % 10 == 0:  # Log every 10 segments
            logger.info(f"Processed {i} segments...")
        transcription += segment.text
    
    total_time = time.time() - start_time
    logger.info(f"Transcription completed in {total_time:.2f}s, transcript length: {len(transcription)} characters")
    
    return transcription
