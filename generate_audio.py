import os
import sys
import json
import requests
import re
from mutagen.mp3 import MP3

PROMPT_FILE = "prompts.txt"
AUDIO_FILE = "voiceover.mp3"
TIMESTAMPS_FILE = "audio_timestamps.json"

def generate_voiceover():
    if not os.path.exists(PROMPT_FILE):
        print(f"❌ {PROMPT_FILE} not found!")
        sys.exit(1)

    # 1. Text read karna aur DOUBLE SAFETY ke liye Numbers delete karna
    lines = []
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                # Sirf Voiceover wali line nikalna
                vo_line = line.split("|")[0].strip()
                # Agar galti se 1. 2. reh gaya ho, to yahan se bhi hatega
                vo_line = re.sub(r'^[\d\.\-\*\s]+', '', vo_line)
                lines.append(vo_line)
                
    if not lines:
        print("❌ No voiceover text found!")
        sys.exit(1)

    full_text = " ".join(lines)
    print(f"🎙️ Text sending to ElevenLabs (Chars: {len(full_text)})...")

    # 🔴 YAHAN APNI ELEVENLABS KI API KEY DAALEIN
    API_KEY = "sk_1ecaa2d5885b536edb08427096f606a9fd1d89fe51a9d90f"
    
    # 🔴 YAHAN APNI PASAND KI VOICE ID DAALEIN
    # (Abhi maine 'Adam' ki ID dali hai jo storytelling ke liye bahut acchi hai)
    VOICE_ID = "eyVoIoi3vo6sJoHOKgAc" 
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": API_KEY
    }
    data = {
        "text": full_text,
        "model_id": "eleven_multilingual_v2", 
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    try:
        print("⏳ Duniya ki sabse REAL AI voice generate ho rahi hai...")
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            with open(AUDIO_FILE, "wb") as f:
                f.write(response.content)
            print("✅ BOOM! Audio generate ho gayi: voiceover.mp3")
        else:
            print(f"❌ ElevenLabs API Error: {response.text}")
            raise Exception("API Failed")
            
    except Exception as e:
        print(f"⚠️ Error: {e}. Dummy timestamps ban rahe hain.")
        timestamps = {str(i+1): 4.0 for i in range(len(lines))}
        with open(TIMESTAMPS_FILE, "w") as f: json.dump(timestamps, f)
        return

    # 3. Timestamp calculation for video sync
    audio = MP3(AUDIO_FILE)
    total_duration = audio.info.length
    total_chars = len(full_text)
    
    timestamps = {}
    for idx, line in enumerate(lines, 1):
        line_duration = (len(line) / total_chars) * total_duration
        timestamps[str(idx)] = round(line_duration + 0.2, 2)

    with open(TIMESTAMPS_FILE, "w") as f:
        json.dump(timestamps, f, indent=4)
        
    print(f"⏱️ Audio Timestamps calculated! Total Duration: {round(total_duration, 2)} sec")

if __name__ == "__main__":
    generate_voiceover()
