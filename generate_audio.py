import os
import json
import time
import requests
from mutagen.mp3 import MP3

AUDIO_DIR = "audio_clips"
SCRIPT_FILE = "script_data.json"
TIMESTAMPS_FILE = "audio_timestamps.json"

# Wahi same API Key jo humne Script banate time use ki thi
XKIRO_API_KEY = os.getenv("XKIRO_API_KEY")

if not XKIRO_API_KEY:
    print("❌ ERROR: XKIRO_API_KEY missing! GitHub Secrets check karein.")
    exit(1)

os.makedirs(AUDIO_DIR, exist_ok=True)

# 🔥 THE MAGIC: Auto-Fallback TTS Models & Voices
# Agar pehla fail hoga toh dusra, phir teesra apne aap try karega!
TTS_COMBINATIONS = [
    {"model": "tts-1", "voice": "onyx"},       # 1st Priority: Deep cinematic male (Fast)
    {"model": "tts-1-hd", "voice": "onyx"},    # 2nd Priority: High-definition deep male
    {"model": "tts-1", "voice": "echo"},       # 3rd Priority: Alternative male voice
    {"model": "tts-1", "voice": "alloy"}       # 4th Priority: Neutral universal voice
]

def generate_line_audio(text, filename):
    url = "https://api.xkiro.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {XKIRO_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Ek-ek karke combination try karega jab tak success na mile
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
            
        time.sleep(2) # Retry se pehle 2 second ka aaram
        
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
        
        # Text clean karna zaroori hai taaki AI ajeeb aawaz na nikale
        clean_text = text.replace("*", "").replace("#", "").strip()
        audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")

        success = generate_line_audio(clean_text, audio_path)
        
        if success and os.path.exists(audio_path):
            # Audio ki timing nikal kar FFmpeg ke liye save karna (0.3s pause ke sath)
            audio = MP3(audio_path)
            duration = round(audio.info.length + 0.3, 2)
            timestamps[str(scene_id)] = duration
            print(f"✅ Scene {scene_id} Audio Ready: {duration}s -> {clean_text[:30]}...")
        else:
            print(f"❌ Failed to generate audio for scene {scene_id}")
            # Fail hone par dummy timing daal denge taaki video render na ruke
            timestamps[str(scene_id)] = 4.0

    with open(TIMESTAMPS_FILE, "w", encoding="utf-8") as f:
        json.dump(timestamps, f, indent=4)
        
    print("🚀 All Premium Audio Clips & Timestamps Generated via xKiro!")

if __name__ == "__main__":
    main()
