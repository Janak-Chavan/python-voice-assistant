import speech_recognition as sr
import sys
import numpy as np
import pyttsx3
from pathlib import Path
from resemblyzer import VoiceEncoder, preprocess_wav

import pyaudiowpatch as pyaudio
sys.modules['pyaudio'] = pyaudio

#Import configuration variables from Configuration.py
import System_Configuration as System_Configuration

# Initialize encoder once
encoder = VoiceEncoder()

# Load reference speaker embeddings
EMBEDDINGS_DIR = Path(System_Configuration.AUDIO_FOLDER_PATH)

speaker_embeddings = {}

# Load speaker profiles from the User_Voice directory
def load_speaker_profiles():
    global speaker_embeddings
    if not EMBEDDINGS_DIR.exists():
        EMBEDDINGS_DIR.mkdir(exist_ok=True)
        print("Created 'audio_samples' directory. Please add 'janak.wav' and 'janhavi.wav' there.")
        return

    for wav_path in EMBEDDINGS_DIR.glob("*.wav"):
        speaker_name = wav_path.stem.lower()
        try:
            wav = preprocess_wav(wav_path)
            embed = encoder.embed_utterance(wav)
            speaker_embeddings[speaker_name] = embed
            print(f"Loaded voice profile for: {speaker_name}")
        except Exception as e:
            print(f"Error loading profile {speaker_name}: {e}")

# Helper function to auto-generate jarvis.wav if missing
def generate_assistant_profile_if_missing():
    assistant_wav_path = EMBEDDINGS_DIR / f"{System_Configuration.AI_NAME}.wav"
    
    if not assistant_wav_path.exists():
        print(f"Assistant voice profile '{assistant_wav_path.name}' missing. Auto-generating using pyttsx3...")
        
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        
        # Select preferred voice (ensure this index matches Speech_System.py)
        if len(voices) > 1:
            engine.setProperty('voice', voices[System_Configuration.AI_VOICE_INDEX].id)
            
        sample_text = "Hello, I am Jarvis. System online and initialized."
        
        # Save directly to .wav file
        engine.save_to_file(sample_text, str(assistant_wav_path))
        engine.runAndWait()
        print(f"Successfully created: {assistant_wav_path.name}")

load_speaker_profiles()
generate_assistant_profile_if_missing()

#Identify the speaker based on the audio file path
def identify_speaker(audio_file_path):
    if not speaker_embeddings:
        print("No speaker profiles loaded. Please add sample .wav files to the 'User_Voice' directory.")
        return "unknown"  # Default fallback if sample files aren't added yet
    
    try:
        test_wav = preprocess_wav(audio_file_path)
        test_embed = encoder.embed_utterance(test_wav)
        
        similarities = {}
        for name, ref_embed in speaker_embeddings.items():
            similarity = np.dot(test_embed, ref_embed) / (np.linalg.norm(test_embed) * np.linalg.norm(ref_embed))
            similarities[name] = similarity
            
        best_match = max(similarities, key=similarities.get)
        print(f"Speaker similarities: {similarities}")  # Debugging line to show similarity scores
        # Confidence score threshold
        if similarities[best_match] > System_Configuration.AUDIO_SIMELRITY_THRESHOLD:
            print(f"Identified speaker: {best_match} with confidence {similarities[best_match]:.2f}")
            if best_match == System_Configuration.AI_NAME:
                print("Detected speech from the AI assistant. Ignoring to prevent feedback loop.")
                return None
            return best_match
    except Exception as e:
        print(f"Speaker identification error: {e}")
        
    return "unknown"  # Return "unknown" if no match is found or an error occurs

#Main function to listen and identify the speaker
def listen():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300 
    recognizer.pause_threshold = 1.0  

    temp_audio_path = System_Configuration.TEMPORARY_FOLDER_PATH + "/temp_audio.wav"
    
    with sr.Microphone() as source:
        print("\nListening... (Speak now)")
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        except sr.WaitTimeoutError:
            print("Listening timed out. No speech detected.")
            return "" , ""
        
    try:
        #Create the temporary folder if it doesn't exist
        if not Path(System_Configuration.TEMPORARY_FOLDER_PATH).exists():
            Path(System_Configuration.TEMPORARY_FOLDER_PATH).mkdir(parents=True, exist_ok=True)

        #Save the recorded audio to a temporary file for speaker identification
        with open(temp_audio_path, "wb") as f:
            f.write(audio.get_wav_data())

        query = recognizer.recognize_google(audio, language='en-in')
        # Identify the speaker using the temporary audio file
        Speaker_name = identify_speaker(temp_audio_path)
        # Check if the User is a human
        if Speaker_name is None:
            return "" , ""
        
        print(f"{Speaker_name}: {query}")
        return query.lower(), Speaker_name
    except sr.UnknownValueError:
        print("Could not understand audio. Try speaking closer to the mic.")
        return "" , ""
    except sr.RequestError:
        print("Network error with speech recognition service.")
        return "" , ""

    finally:
        # This deletes the temporary file automatically every time, success or fail
        if Path(temp_audio_path).exists():
            Path(temp_audio_path).unlink()
