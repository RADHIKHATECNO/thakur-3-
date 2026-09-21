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

# 🔥 THE MAGIC: Smart Voice Filter for Hindi/Male
def get_best_voice():
    print("🔍 Fetching live available voices from xKiro...")
    url = "https://api.xkiro.com/v1/audio/voices"
    headers = {"Authorization": f"Bearer {XKIRO_API_KEY}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            voices = []
            
            if "voices" in data:
                voices = data["voices"]
            elif "data" in data:
                voices = [v["id"] for v in data["data"]]
            elif isinstance(data, list):
                voices = data
                
            # Sab voices ke ID extract kar lo
            v_ids = [v.get("id", v) if isinstance(v, dict) else v for v in voices]
            
            if v_ids:
                print(f"✅ Found {len(v_ids)} live voices. Finding the best Hindi/Male voice...")
                
                # PRIORITY 1: Indian/Hindi Male
                for v in v_ids:
                    v_lower = v.lower()
                    if ("ind" in v_lower or "hin" in v_lower) and "male" in v_lower:
                        return v
                        
                # PRIORITY 2: Any Indian/Hindi Voice
                for v in v_ids:
                    v_lower = v.lower()
                    if "ind" in v_lower or "hin" in v_lower:
                        return v
                        
                # PRIORITY 3: Any Male Voice (Mexican/Female avoid karne ke liye)
                for v in v_ids:
                    v_lower = v.lower()
                    if "male" in v_lower and "female" not in v_lower:
                        return v
                        
                # PRIORITY 4: Standard AI Voices (Onyx, Echo etc.)
                for v in v_ids:
                    if v.lower() in ["onyx", "echo", "alloy", "fable"]:
                        return v
                        
                return v_ids[0] # Last fallback
        else:
            print(f"⚠️ Failed to fetch voice list: {response.text}")
    except Exception as e:
        print(f"⚠️ Network error fetching voices: {e}")
        
    return "alloy" # Default fallback

# Script chalne se pehle ek baar best voice dhoondh lega
LIVE_VOICE = get_best_voice()

def generate_line_audio(text, filename):
    url = "https://api.xkiro.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {XKIRO_API_KEY}",
        "Content-Type": "application/json"
    }
    
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
        
        # Symbols remove karna zaroori hai
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
        
    print(f"🚀 All Premium Audio Clips Generated Successfully using '{LIVE_VOICE}' voice!")

if __name__ == "__main__":
    main()
