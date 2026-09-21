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

# 🔥 THE MAGIC: Auto-Fetch Live Voices from xKiro!
def get_live_voice():
    print("🔍 Fetching live available voices from xKiro...")
    url = "https://api.xkiro.com/v1/audio/voices"
    headers = {"Authorization": f"Bearer {XKIRO_API_KEY}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            voices = []
            
            # API JSON ka format kuch bhi ho, hum usme se voices nikal lenge
            if "voices" in data:
                voices = data["voices"]
            elif "data" in data:
                voices = [v["id"] for v in data["data"]]
            elif isinstance(data, list):
                voices = [v.get("id", v) if isinstance(v, dict) else v for v in data]
                
            if voices:
                print(f"✅ Found {len(voices)} live voices! (Using the first one: '{voices[0]}')")
                # Pehli available voice ko return kar raha hai
                valid_voice = voices[0] 
                if isinstance(valid_voice, dict) and "id" in valid_voice:
                    return valid_voice["id"]
                return valid_voice
        else:
            print(f"⚠️ Failed to fetch voice list: {response.text}")
    except Exception as e:
        print(f"⚠️ Network error fetching voices: {e}")
        
    print("⚠️ Fallback to 'default' voice.")
    return "default"

# Get the voice once before looping
LIVE_VOICE = get_live_voice()

def generate_line_audio(text, filename):
    url = "https://api.xkiro.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {XKIRO_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Ab fail hone ka chance nahi kyunki hum wo voice de rahe hain jo server ne khud di hai
    model = "xkiro-voice"
    print(f"🔄 Generating TTS... Model: '{model}' | Voice: '{LIVE_VOICE}'")
    
    data = {
        "model": model,
        "input": text,
        "voice": LIVE_VOICE
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)
            return True
        else:
            print(f"⚠️ xKiro TTS Error: {response.text}")
    except Exception as e:
        print(f"⚠️ Network Failed: {e}")
        
    time.sleep(2)
    return False

def main():
    if not os.path.exists(SCRIPT_FILE):
        print("❌ ERROR: script_data.json nahi mili!")
        return

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    timestamps = {}
    print(f"🎙️ Generating Audio for {len(scenes)} scenes...")

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
        
    print("🚀 All Premium Audio Clips Generated Successfully!")

if __name__ == "__main__":
    main()
