import os
import json
import time
import requests
import base64
import subprocess
from mutagen.mp3 import MP3

AUDIO_DIR = "audio_clips"
SCRIPT_FILE = "script_data.json"
TIMESTAMPS_FILE = "audio_timestamps.json"

# 🔥 GNANI API KEY (GitHub Secrets se aayegi)
GNANI_API_KEY = os.getenv("GNANI_API_KEY")

if not GNANI_API_KEY:
    print("❌ ERROR: GNANI_API_KEY nahi mili! Kripya GitHub Secrets check karein.")
    exit(1)

os.makedirs(AUDIO_DIR, exist_ok=True)

def generate_line_audio(text, filename):
    # Gnani.ai official REST API URL for TTS (timbre model)
    url = "https://api.vachana.ai/api/v1/tts/inference"
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key-ID": GNANI_API_KEY
    }
    
    # Strictly matching the official timbre-v2.0 schema for 'Deepak'
    data = {
        "text": text,
        "voice": "Deepak",          # 🔥 Deepak Voice (Male, Grounded, Conversational)
        "model": "timbre-v2.0",     # Deepak voice belongs to timbre-v2.0 model
        "audio_config": {
            "sample_rate": 44100,   # High-quality rendering
            "encoding": "linear_pcm",
            "container": "wav"
        }
    }
    
    for attempt in range(1, 4):
        try:
            print(f"📡 Requesting Gnani.ai for voice 'Deepak' (Attempt {attempt})...")
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                resp_json = response.json()
                
                # Gnani returns base64 string in "audio" parameter or direct dict
                # Standard REST base64 audio response retrieval
                audio_base64 = resp_json.get("audio", "")
                if audio_base64:
                    audio_data = base64.b64decode(audio_base64)
                    with open(filename, "wb") as f:
                        f.write(audio_data)
                    return True
                else:
                    print("⚠️ Audio key not found in response JSON structure.")
            else:
                print(f"⚠️ Gnani.ai TTS Error: {response.text}")
        except Exception as e:
            print(f"⚠️ Connection/Decoding Failed: {e}")
            
        time.sleep(2)
        
    return False

def main():
    if not os.path.exists(SCRIPT_FILE):
        print("❌ ERROR: script_data.json nahi mili!")
        return

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    timestamps = {}
    print(f"🎙️ Generating High-Quality Audio using Gnani's 'Deepak' Voice...")

    for scene in scenes:
        scene_id = scene.get("scene")
        text = scene.get("narration")
        
        # Clean text
        clean_text = text.replace("*", "").replace("#", "").strip()
        audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.wav") 

        success = generate_line_audio(clean_text, audio_path)
        
        if success and os.path.exists(audio_path):
            mp3_path = audio_path.replace(".wav", ".mp3")
            
            # Convert WAV to MP3 using FFmpeg
            subprocess_cmd = [
                "ffmpeg", "-y", "-i", audio_path, 
                "-codec:a", "libmp3lame", "-b:a", "192k", 
                mp3_path
            ]
            subprocess.run(subprocess_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Exact duration calculation (Mutagen MP3)
            audio = MP3(mp3_path)
            duration = round(audio.info.length + 0.3, 2)
            timestamps[str(scene_id)] = duration
            
            # WAV file delete karein
            os.remove(audio_path)
            
            print(f"✅ Scene {scene_id} Audio Ready: {duration}s -> {clean_text[:30]}...")
        else:
            print(f"❌ Failed to generate audio for scene {scene_id}")
            timestamps[str(scene_id)] = 4.0

    with open(TIMESTAMPS_FILE, "w", encoding="utf-8") as f:
        json.dump(timestamps, f, indent=4)
        
    print("🚀 All Premium Deepak-Voice Audio Clips Ready!")

if __name__ == "__main__":
    main()
