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

# 🔥 GNANI API KEY (GitHub Secrets)
GNANI_API_KEY = os.getenv("GNANI_API_KEY")

if not GNANI_API_KEY:
    print("❌ ERROR: GNANI_API_KEY nahi mili!")
    exit(1)

os.makedirs(AUDIO_DIR, exist_ok=True)

def generate_full_story_audio(full_text, output_wav):
    # Gnani.ai official REST API URL for TTS
    url = "https://api.vachana.ai/api/v1/tts/inference"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key-ID": GNANI_API_KEY
    }
    
    # 🔥 FIXED: Using 'timbre-v2.5' model as per latest documentation!
    data = {
        "text": full_text,
        "voice": "Deepak",          # Deepak Voice (Pure Hindi Male)
        "model": "timbre-v2.5",     # UPDATED TO THE LATEST SUPPORTED MODEL!
        "audio_config": {
            "sample_rate": 44100,   
            "encoding": "linear_pcm",
            "container": "wav"
        }
    }
    
    for attempt in range(1, 4):
        try:
            print(f"📡 Requesting Gnani.ai for One-Shot Voiceover with 'Deepak' using timbre-v2.5...")
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                resp_json = response.json()
                audio_base64 = resp_json.get("audio", "")
                if audio_base64:
                    audio_data = base64.b64decode(audio_base64)
                    with open(output_wav, "wb") as f:
                        f.write(audio_data)
                    return True
            else:
                print(f"⚠️ Gnani.ai TTS Error: {response.text}")
        except Exception as e:
            print(f"⚠️ Connection/Decoding Failed: {e}")
            
        time.sleep(3)
    return False

def main():
    if not os.path.exists(SCRIPT_FILE):
        print("❌ ERROR: script_data.json nahi mili!")
        return

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    # 1. Puri script ka ek continuous paragraph banana (Pause markers ke sath)
    full_text_list = []
    for scene in scenes:
        narration = scene.get("narration", "").strip()
        if narration:
            # Natural pauses ke liye commas/periods handle karna
            if not narration.endswith(('.', '!', '?', ',')):
                narration += "."
            full_text_list.append(narration)

    full_text = " ".join(full_text_list)
    print(f"🎙️ Full Story Length: {len(full_text)} characters.")
    
    full_wav_path = os.path.join(AUDIO_DIR, "full_story.wav")
    
    # 2. Continuous voice generation (Pure continuous human flow)
    success = generate_full_story_audio(full_text, full_wav_path)
    
    if not success or not os.path.exists(full_wav_path):
        print("❌ Failed to generate full story audio.")
        exit(1)
        
    # WAV to MP3 conversion using FFmpeg
    full_mp3_path = os.path.join(AUDIO_DIR, "full_story.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-i", full_wav_path, 
        "-codec:a", "libmp3lame", "-b:a", "192k", 
        full_mp3_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    audio = MP3(full_mp3_path)
    total_duration = audio.info.length
    print(f"✅ Full Audio generated successfully! Duration: {round(total_duration, 2)} seconds.")
    
    # 3. Slicing logic for each scene proportionate to text length
    timestamps = {}
    total_chars = len(full_text)
    current_time = 0.0
    
    print("✂️ Slicing audio files and calculating exact scene timings...")
    for idx, scene in enumerate(scenes, 1):
        scene_id = str(scene["scene"])
        scene_text = scene.get("narration", "").strip()
        
        scene_char_count = len(scene_text)
        scene_duration = (scene_char_count / total_chars) * total_duration
        scene_duration = round(scene_duration + 0.3, 2) # Added pause buffer
        
        timestamps[scene_id] = scene_duration
        
        # Split main file into small scene MP3 files
        scene_wav_output = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(current_time), "-t", str(scene_duration), 
            "-i", full_mp3_path, "-acodec", "copy", scene_wav_output
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        current_time += scene_duration
        print(f"   👉 Scene {scene_id} timing: {scene_duration}s")
        
    # Clean temporary master files
    if os.path.exists(full_wav_path): os.remove(full_wav_path)
    if os.path.exists(full_mp3_path): os.remove(full_mp3_path)

    # Save exact timestamps for FFmpeg
    with open(TIMESTAMPS_FILE, "w", encoding="utf-8") as f:
        json.dump(timestamps, f, indent=4)
        
    print("🚀 One-Shot Voiceover process completed successfully!")

if __name__ == "__main__":
    main()
