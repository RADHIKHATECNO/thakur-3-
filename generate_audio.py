import os
import json
import time
import requests
import base64
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
    # Gnani.ai official REST API URL
    url = "https://api.vachana.ai/api/v1/tts/inference" # Standard REST TTS
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key-ID": GNANI_API_KEY # Authentication header
    }
    
    # Payload configured for "Deepak" Hindi voice
    data = {
        "text": text,
        "voice": "Deepak",          # 🔥 Deepak Voice selected!
        "model": "timbre-v2.5",     # Premium Recommended Model
        "language": "hi-IN",        # Hindi
        "speed": 0.95,              # Thoda slow aur deep voice ke liye
        "audio_config": {
            "sample_rate": 44100,   # Standard High Quality
            "encoding": "linear_pcm", # Standard raw audio
            "container": "wav"      # WAV container is safer
        }
    }
    
    for attempt in range(1, 4):
        try:
            print(f"📡 Requesting Gnani.ai for voice 'Deepak' (Attempt {attempt})...")
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                # Direct binary content save karna
                with open(filename, "wb") as f:
                    f.write(response.content)
                return True
            else:
                print(f"⚠️ Gnani.ai TTS Error: {response.text}")
        except Exception as e:
            print(f"⚠️ Connection Failed: {e}")
            
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
        # WAV format is used for high-fidelity rendering
        audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.wav") 

        success = generate_line_audio(clean_text, audio_path)
        
        if success and os.path.exists(audio_path):
            # FFmpeg ke zariye WAV ko MP3 mein convert karenge taaki timing calculate ho sake
            mp3_path = audio_path.replace(".wav", ".mp3")
            subprocess_cmd = [
                "ffmpeg", "-y", "-i", audio_path, 
                "-codec:a", "libmp3lame", "-b:a", "192k", 
                mp3_path
            ]
            subprocess.run(subprocess_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Duration check (mp3)
            audio = MP3(mp3_path)
            duration = round(audio.info.length + 0.3, 2)
            timestamps[str(scene_id)] = duration
            
            # Purani WAV file delete kar do
            os.remove(audio_path)
            
            print(f"✅ Scene {scene_id} Audio Ready: {duration}s -> {clean_text[:30]}...")
        else:
            print(f"❌ Failed to generate audio for scene {scene_id}")
            # Fallback to dummy duration to prevent crash
            timestamps[str(scene_id)] = 4.0

    with open(TIMESTAMPS_FILE, "w", encoding="utf-8") as f:
        json.dump(timestamps, f, indent=4)
        
    print("🚀 All Premium Deepak-Voice Audio Clips Ready!")

if __name__ == "__main__":
    # Import subprocess within main to avoid startup delays
    import subprocess 
    main()
