import os
import sys
import json
import requests
import subprocess

# Mutagen library to calculate mp3 duration easily
try:
    from mutagen.mp3 import MP3
except ImportError:
    os.system("pip install mutagen")
    from mutagen.mp3 import MP3

API_KEY = os.getenv("ELEVENLABS_API_KEY")
PROMPT_FILE = "prompts.txt"
AUDIO_FILE = "voiceover.mp3"
TIMESTAMPS_FILE = "audio_timestamps.json"

# Voice ID (Adam - Deep, narrative voice. You can change this ID if you want a different voice)
VOICE_ID = "pNInz6obpgDQGcFmaJgB" 

def generate_voiceover():
    if not os.path.exists(PROMPT_FILE):
        print(f"❌ {PROMPT_FILE} not found!")
        sys.exit(1)

    # 1. Read all Voiceover lines
    lines = []
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                lines.append(line.split("|")[0].strip())
                
    if not lines:
        print("❌ No voiceover text found in prompts.txt!")
        sys.exit(1)

    full_text = " ".join(lines)
    print(f"🎙️ Sending text to ElevenLabs (Total Characters: {len(full_text)})...")

    # 2. Call ElevenLabs API
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": API_KEY
    }
    data = {
        "text": full_text,
        "model_id": "eleven_multilingual_v2", # Best for Hindi/Hinglish & English
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.7
        }
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 200:
            print(f"❌ ElevenLabs API Error: {response.text}")
            raise Exception("API Failed")
            
        with open(AUDIO_FILE, "wb") as f:
            f.write(response.content)
        print("✅ voiceover.mp3 generated successfully!")
        
    except Exception as e:
        print(f"⚠️ Voiceover generation failed: {e}. Creating dummy timestamps.")
        # Fallback if API limit is reached
        timestamps = {str(i+1): 4.0 for i in range(len(lines))}
        with open(TIMESTAMPS_FILE, "w") as f: json.dump(timestamps, f)
        return

    # 3. Calculate Timestamps (Perfect Sync Logic)
    # We calculate the total duration, and divide it proportionally by the length of each sentence.
    audio = MP3(AUDIO_FILE)
    total_duration = audio.info.length
    total_chars = len(full_text)
    
    timestamps = {}
    for idx, line in enumerate(lines, 1):
        # Time for this line = (Characters in this line / Total Characters) * Total Duration
        line_duration = (len(line) / total_chars) * total_duration
        # Add 0.2s padding for natural pauses
        timestamps[str(idx)] = round(line_duration + 0.2, 2)

    with open(TIMESTAMPS_FILE, "w") as f:
        json.dump(timestamps, f, indent=4)
        
    print(f"⏱️ Audio Timestamps calculated perfectly! Total Duration: {round(total_duration, 2)} seconds")
    print(json.dumps(timestamps, indent=4))

if __name__ == "__main__":
    generate_voiceover()
