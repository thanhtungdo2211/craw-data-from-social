from faster_whisper import WhisperModel

model_size = "large-v3"
model = WhisperModel(model_size, device="cpu", compute_type="int8")

def audio_to_transcript(audio_path):
    segments, info = model.transcribe(audio_path, beam_size=5)

    print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

    transcription = ""
    
    for segment in segments:
        # text = segment.text.strip()
        # print(f"{text}")
        transcription += segment.text 

    return transcription