import os
import json
import asyncio
import edge_tts
from mutagen.mp3 import MP3

AUDIO_DIR = "audio_clips"
SCRIPT_FILE = "script_data.json"
TIMESTAMPS_FILE = "audio_timestamps.json"

# 🔥 PERFECT HINDI VOICE (Microsoft's Premium AI)
VOICE = "hi-IN-MadhurNeural" # Male Storyteller
RATE = "-5%"  # Thoda slow aur deep
PITCH = "-2Hz" # Bhaari aawaz

os.makedirs(AUDIO_DIR, exist_ok=True)

async def generate_line_audio(text, filename):
    try:
        communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
        await communicate.save(filename)
        return True
    except Exception as e:
        print(f"⚠️ Error generating audio: {e}")
        return False

async def main():
    if not os.path.exists(SCRIPT_FILE):
        print("❌ ERROR: script_data.json nahi mili!")
        return

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    timestamps = {}
    print(f"🎙️ Generating Perfect Hindi Audio using {VOICE}...")

    for scene in scenes:
        scene_id = scene.get("scene")
        text = scene.get("narration")
        
        # Clean text
        clean_text = text.replace("*", "").replace("#", "").strip()
        audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")

        print(f"🔄 Processing Scene {scene_id}...")
        success = await generate_line_audio(clean_text, audio_path)
        
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
        
    print("🚀 All Premium Hindi Audio Clips Generated Successfully!")

if __name__ == "__main__":
    asyncio.run(main())
