import os
import json
import asyncio
import subprocess
import edge_tts
from mutagen.mp3 import MP3

AUDIO_DIR = "audio_clips"
SCRIPT_FILE = "script_data.json"
TIMESTAMPS_FILE = "audio_timestamps.json"

# 🔥 100% FREE UNLIMITED VOICE (Microsoft Premium)
VOICE = "hi-IN-MadhurNeural"
RATE = "-5%"   # Thoda slowly bolega suspense ke liye
PITCH = "-4Hz" # Aawaz aur bhaari karne ke liye

os.makedirs(AUDIO_DIR, exist_ok=True)

async def generate_line_audio(text, filename):
    temp_file = filename.replace(".mp3", "_temp.mp3")
    try:
        # 1. Generate Raw Free Audio
        communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
        await communicate.save(temp_file)

        # 2. 🎛️ HOLLYWOOD STUDIO MASTERING (The ElevenLabs Hack)
        # Filters: Bass boost, Treble crispness, Dynamic Compression (Punchy), Subtle Echo
        mastering_filter = (
            "bass=g=10:f=110:w=0.3,"          # Bass (Bhaari-pan) +10dB
            "treble=g=5:f=3000:w=0.2,"        # Crispness +5dB
            "compand=attacks=0:points=-80/-80|-15/-15|0/-1.2|20/-1.2:gain=4," # Radio Host Loudness
            "aecho=0.8:0.88:15:0.05"          # Subtle Cinematic Studio Room Echo
        )
        
        # Apply FFmpeg Audio Magic
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_file, 
            "-af", mastering_filter, 
            filename
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Delete raw file
        os.remove(temp_file)
        return True
    except Exception as e:
        print(f"⚠️ Audio Mastering Error: {e}")
        return False

async def main():
    if not os.path.exists(SCRIPT_FILE):
        print("❌ ERROR: script_data.json nahi mili!")
        return

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    timestamps = {}
    print("🎙️ Generating & Mastering Cinematic Voice (100% Free/Unlimited)...")

    for scene in scenes:
        scene_id = scene.get("scene")
        text = scene.get("narration")
        
        clean_text = text.replace("*", "").replace("#", "").strip()
        audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")

        success = await generate_line_audio(clean_text, audio_path)
        
        if success and os.path.exists(audio_path):
            audio = MP3(audio_path)
            duration = round(audio.info.length + 0.3, 2)
            timestamps[str(scene_id)] = duration
            print(f"✅ Scene {scene_id} Studio Audio Ready: {duration}s -> {clean_text[:30]}...")
        else:
            print(f"❌ Failed audio for scene {scene_id}")
            timestamps[str(scene_id)] = 4.0

    with open(TIMESTAMPS_FILE, "w", encoding="utf-8") as f:
        json.dump(timestamps, f, indent=4)
        
    print("🚀 All Premium Studio Mastered Audio Clips Ready!")

if __name__ == "__main__":
    asyncio.run(main())
