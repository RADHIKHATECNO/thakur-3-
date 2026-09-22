import os
import json
import time
import requests
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
    url = "https://api.vachana.ai/api/v1/tts/inference"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key-ID": GNANI_API_KEY
    }
    
    # Strictly matching the official timbre-v2.5 schema for 'Deepak' with hi-IN language
    data = {
        "text": full_text,
        "voice": "Deepak",          # Deepak Voice (Pure Hindi Male)
        "model": "timbre-v2.5",     # Latest timbre-v2.5 model
        "language": "hi-IN",        # Required for timbre-v2.5 multilingual voices!
        "speed": 0.95,              # Suspense aur depth ke liye perfect speed
        "audio_config": {
            "sample_rate": 44100,   
            "encoding": "linear_pcm",
            "container": "wav"
        }
    }
    
    for attempt in range(1, 4):
        try:
            print(f"📡 Requesting Gnani.ai for One-Shot Voiceover with 'Deepak' (timbre-v2.5)...")
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            # 🔥 THE FIX: Gnani REST API returns direct RAW binary wav! No JSON decoding needed!
            if response.status_code == 200:
                print("✅ Successfully received raw binary audio from Gnani.ai!")
                with open(output_wav, "wb") as f:
                    f.write(response.content) # Writing direct binary bytes
                return True
            else:
                print(f"⚠️ Gnani.ai TTS Error: Status {response.status_code} | Details: {response.text}")
        except Exception as e:
            print(f"⚠️ Connection Failed: {e}")
            
        time.sleep(3)
    return False

def main():
    if not os.path.exists(SCRIPT_FILE):
        print("❌ ERROR: script_data.json nahi mili!")
        return

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    # 1. Join all scene narrations into one continuous paragraph
    full_text_list = []
    for scene in scenes:
        narration = scene.get("narration", "").strip()
        if narration:
            if not narration.endswith(('.', '!', '?', ',')):
                narration += "."
            full_text_list.append(narration)

    full_text = " ".join(full_text_list)
    print(f"🎙️ Full Story Length: {len(full_text)} characters.")
    
    full_wav_path = os.path.join(AUDIO_DIR, "full_story.wav")
    
    # 2. Call Gnani API for raw WAV file
    success = generate_full_story_audio(full_text, full_wav_path)
    
    if not success or not os.path.exists(full_wav_path):
        print("❌ Failed to generate full story audio.")
        exit(1)
        
    # Convert Full WAV to High Quality MP3 via FFmpeg
    full_mp3_path = os.path.join(AUDIO_DIR, "full_story.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-i", full_wav_path, 
        "-codec:a", "libmp3lame", "-b:a", "192k", 
        full_mp3_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Read MP3 metadata to calculate exact duration
    audio = MP3(full_mp3_path)
    total_duration = audio.info.length
    print(f"✅ Full Audio generated successfully! Duration: {round(total_duration, 2)} seconds.")
    
    # 3. Cut master MP3 into small scene clips
    timestamps = {}
    total_chars = len(full_text)
    current_time = 0.0
    
    print("✂️ Slicing audio files and calculating exact scene timings...")
    for idx, scene in enumerate(scenes, 1):
        scene_id = str(scene["scene"])
        scene_text = scene.get("narration", "").strip()
        
        scene_char_count = len(scene_text)
        scene_duration = (scene_char_count / total_chars) * total_duration
        scene_duration = round(scene_duration + 0.3, 2) # Adding brief pause buffer
        
        timestamps[scene_id] = scene_duration
        
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

    # Save calculated timestamps
    with open(TIMESTAMPS_FILE, "w", encoding="utf-8") as f:
        json.dump(timestamps, f, indent=4)
        
    print("🚀 One-Shot Voiceover process completed successfully!")

if __name__ == "__main__":
    main()
