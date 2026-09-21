import os
import json
import asyncio
import edge_tts
from mutagen.mp3 import MP3

AUDIO_DIR = "audio_clips"
SCRIPT_FILE = "script_data.json"
TIMESTAMPS_FILE = "audio_timestamps.json"

# Voice Settings (Best Hindi Male Voice)
VOICE = "hi-IN-MadhurNeural"
RATE = "-5%"  # Thoda slow taaki suspense bane
PITCH = "-2Hz" # Bhaari aur cinematic aawaz

os.makedirs(AUDIO_DIR, exist_ok=True)

async def generate_line_audio(text, filename):
    # Edge-TTS ekdum free aur unlimited hai GitHub Actions par!
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    await communicate.save(filename)

async def main():
    if not os.path.exists(SCRIPT_FILE):
        print("❌ ERROR: script_data.json nahi mili! Pehle script generate karein.")
        return

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    timestamps = {}
    print(f"🎙️ Generating High-Quality Professional Audio for {len(scenes)} scenes...")

    for scene in scenes:
        scene_id = scene.get("scene")
        text = scene.get("narration")
        
        # Text clean karna taaki AI ajeeb symbols na padhe
        clean_text = text.replace("*", "").replace("#", "").strip()
        audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")

        # Audio Generate karna
        await generate_line_audio(clean_text, audio_path)

        # Exact timing calculate karna (Syncing ke liye zaruri hai)
        audio = MP3(audio_path)
        # 0.3 second ka pause buffer joda hai taaki scenes ke beech natural saans lene ka time mile
        duration = round(audio.info.length + 0.3, 2) 

        timestamps[str(scene_id)] = duration
        print(f"✅ Scene {scene_id} Audio Ready: {duration}s -> {clean_text[:40]}...")

    # Timestamps save karna FFmpeg ke liye
    with open(TIMESTAMPS_FILE, "w", encoding="utf-8") as f:
        json.dump(timestamps, f, indent=4)
        
    print("🚀 All Audio Clips & Timestamps Generated Successfully!")

if __name__ == "__main__":
    asyncio.run(main())
