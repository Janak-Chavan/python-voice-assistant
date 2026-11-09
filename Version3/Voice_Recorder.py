import sounddevice as sd
import soundfile as sf
import os

import System_Configuration as System_Configuration

def record_audio():
    if not os.path.exists(System_Configuration.AUDIO_FOLDER_PATH):
        os.makedirs(System_Configuration.AUDIO_FOLDER_PATH, exist_ok=True)
    name = input("Press Enter when You are ready to speak and enter your name :- ")

    duration = System_Configuration.VOICE_FILE_DURATION
    sample_rate = 16000

    print(f"Recording for {name}... Speak now!")
    audio_janak = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
    sd.wait()
    sf.write(f"{System_Configuration.AUDIO_FOLDER_PATH}/{name}.wav", audio_janak, sample_rate)
    print(f"Saved {name}.wav successfully!")

record_audio()