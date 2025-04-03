from transformers import pipeline
transcriber = pipeline("automatic-speech-recognition", model="vinai/PhoWhisper-small")
output = transcriber("data/audio/bbc44855-d6a0-422d-92b7-4ff5bf507be0.mp3",  chunk_length_s=30, batch_size=16)['text']

print(output)