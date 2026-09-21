import os
import json
import time
import requests
from mutagen.mp3 import MP3

AUDIO_DIR = "audio_clips"
SCRIPT_FILE = "script_data.json"
TIMESTAMPS_FILE = "audio_timestamps.json"

XKIRO_API_KEY = os.getenv("XKIRO_API_KEY")

if not XKIRO_API_KEY:
    print("❌ ERROR: XKIRO_API_KEY missing! GitHub Secrets check karein.")
    exit(1)

os.makedirs(AUDIO_DIR, exist_ok=True)

# 🔥 FIX: xKiro ne model ka naam badal kar "xkiro-voice" kar diya hai!
TTS_COMBINATIONS = [
    {"model": "xkiro-voice", "voice": "onyx"},       # 1st: Deep cinematic male
    {"model": "xkiro-voice", "voice": "echo"},       # 2nd: Alternative male
    {"model": "xkiro-voice", "voice": "alloy"}       # 3rd: Neutral voice
]

def generate_line_audio(text, filename):
    url = "https://api.xkiro.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {XKIRO_API_KEY}",
        "Content-Type": "application/json"
    }
    
    for combo in TTS_COMBINATIONS:
        model = combo["model"]
        voice = combo["voice"]
        print(f"🔄 Trying TTS Model: '{model}' | Voice: '{voice}'...")
        
        data = {
            "model": model,
            "input": text,
            "voice": voice
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(response.content)
                return True
            else:
                print(f"⚠️ xKiro TTS Error ({model}/{voice}): {response.text}")
        except Exception as e:
            print(f"⚠️ Network Failed ({model}/{voice}): {e}")
            
        time.sleep(2)
        
    return False

def main():
    if not os.path.exists(SCRIPT_FILE):
        print("❌ ERROR: script_data.json nahi mili!")
        return

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    timestamps = {}
    print(f"🎙️ Generating Auto-Fallback AI Voice via xKiro for {len(scenes)} scenes...")

    for scene in scenes:
        scene_id = scene.get("scene")
        text = scene.get("narration")
        
        clean_text = text.replace("*", "").replace("#", "").strip()
        audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")

        success = generate_line_audio(clean_text, audio_path)
        
        if success and os.path.exists(audio_path):
            audio = MP3(audio_path)
            duration = round(audio.info.length + 0.3, 2)
            timestamps[str(scene_id)] = duration
            print(f"✅ Scene {scene_id} Audio Ready: {duration}s -> {clean_text[:30]}...")
        else:
            print(f"❌ Failed to generate audio for scene {scene_id}")
            timestamps[str(scene_id)] = 4.0

    with open(TIMESTAMPS_FILE, "w", encoding="utf-8") as f:
        json.dump(timestamps, f, indent=4)
        
    print("🚀 All Premium Audio Clips & Timestamps Generated via xKiro!")

if __name__ == "__main__":
    main()
