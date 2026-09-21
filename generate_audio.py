import os
import sys
import json
import asyncio
import edge_tts
from mutagen.mp3 import MP3

PROMPT_FILE = "prompts.txt"
TIMESTAMPS_FILE = "audio_timestamps.json"
AUDIO_DIR = "audio_clips"

# Professional Hindi Voice Settings
VOICE = "hi-IN-MadhurNeural" # Male Storyteller voice
RATE = "-5%" # Thoda slow taaki suspense bane
PITCH = "-2Hz" # Thodi bhaari aawaz

os.makedirs(AUDIO_DIR, exist_ok=True)

async def generate_line_audio(text, filename):
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    await communicate.save(filename)

async def main():
    if not os.path.exists(PROMPT_FILE):
        sys.exit(1)
        
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        lines = [line.split("|")[0].strip() for line in f if "|" in line]
        
    timestamps = {}
    master_list = []
    
    print(f"🎙️ Generating High-Quality Professional Audio with {VOICE}...")
    
    for idx, text in enumerate(lines, 1):
        clean_text = text.replace("*", "").replace("#", "")
        audio_path = os.path.join(AUDIO_DIR, f"line_{idx}.mp3")
        
        # Generate Audio via Edge TTS
        await generate_line_audio(clean_text, audio_path)
        
        # Exact length calculation
        audio = MP3(audio_path)
        duration = round(audio.info.length + 0.3, 2) # Added 0.3s pause buffer
        
        timestamps[str(idx)] = duration
        master_list.append(f"file '{audio_path}'")
        print(f"✅ Scene {idx} Audio: {duration}s -> {clean_text[:40]}...")

    with open(TIMESTAMPS_FILE, "w") as f:
        json.dump(timestamps, f, indent=4)
        
    # Create FFmpeg list for joining audio later
    with open(os.path.join(AUDIO_DIR, "audio_list.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(master_list))
        
    print("✅ All Audio Clips and Timestamps Generated Successfully!")

if __name__ == "__main__":
    asyncio.run(main())
