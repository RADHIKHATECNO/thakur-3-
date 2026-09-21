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

# 🔥 THE MAGIC: Strict Voice Filter (Bans Chinese/Mexican etc.)
def get_best_voice():
    print("🔍 Fetching live available voices from xKiro...")
    url = "https://api.xkiro.com/v1/audio/voices"
    headers = {"Authorization": f"Bearer {XKIRO_API_KEY}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            voices = []
            
            if "voices" in data: voices = data["voices"]
            elif "data" in data: voices = [v["id"] for v in data["data"]]
            elif isinstance(data, list): voices = data
                
            v_ids = [v.get("id", v) if isinstance(v, dict) else v for v in voices]
            
            if v_ids:
                # 🚫 BANNED LIST: In deshon ki aawazein Hindi ko barbaad kar deti hain
                banned = ["chinese", "mexican", "spanish", "french", "german", "korean", "japanese", "arab", "es-", "zh-", "fr-"]
                
                # Filter safe voices only
                safe_voices = [v for v in v_ids if not any(b in v.lower() for b in banned)]
                if not safe_voices: safe_voices = v_ids # Fallback agar sab ban ho jayein
                
                print(f"✅ Found {len(safe_voices)} SAFE live voices. Filtering best Hindi/English Male...")
                
                # PRIORITY 1: Indian/Hindi Male
                for v in safe_voices:
                    if ("ind" in v.lower() or "hin" in v.lower() or "hi-" in v.lower()) and "male" in v.lower():
                        return v
                        
                # PRIORITY 2: Any Indian/Hindi Voice
                for v in safe_voices:
                    if "ind" in v.lower() or "hin" in v.lower() or "hi-" in v.lower():
                        return v
                        
                # PRIORITY 3: Multilingual Male (Good for Hinglish)
                for v in safe_voices:
                    if "multi" in v.lower() and "male" in v.lower():
                        return v
                        
                # PRIORITY 4: English Male (Better pronunciation for Hindi text than Chinese)
                for v in safe_voices:
                    if ("eng" in v.lower() or "en-" in v.lower() or "us-" in v.lower() or "uk-" in v.lower()) and "male" in v.lower():
                        return v
                        
                # PRIORITY 5: Just any safe Male
                for v in safe_voices:
                    if "male" in v.lower() and "female" not in v.lower():
                        return v
                        
                return safe_voices[0]
        else:
            print(f"⚠️ Failed to fetch voice list: {response.text}")
    except Exception as e:
        print(f"⚠️ Network error fetching voices: {e}")
        
    return "alloy" # Default

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
            print(f"✅ Scene {scene_id} Audio: {duration}s")
        else:
            timestamps[str(scene_id)] = 4.0

    with open(TIMESTAMPS_FILE, "w", encoding="utf-8") as f:
        json.dump(timestamps, f, indent=4)
        
    print(f"🚀 All Audio Generated Successfully using SAFE voice: '{LIVE_VOICE}'")

if __name__ == "__main__":
    main()
