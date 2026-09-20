import os
import sys
import json
import time
import subprocess
import requests

# ============================================================
# CONFIG
# ============================================================
PROMPT_FILE = "prompts.txt"
CONFIG_FILE = "video_config.json"
VOICE_DIR   = "scene_voices"
os.makedirs(VOICE_DIR, exist_ok=True)

# ============================================================
# KOKORO TTS INSTALLER
# ============================================================
def install_kokoro():
    """
    Kokoro TTS install karo
    """
    print("📦 Installing Kokoro TTS...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", 
             "kokoro-onnx", "soundfile", "numpy"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ Kokoro TTS installed!")
        return True
    except Exception as e:
        print(f"❌ Kokoro install failed: {e}")
        return False

# ============================================================
# HINDI TRANSLITERATOR
# ============================================================
def prepare_hindi_text(text):
    """
    Hindi text ko Kokoro ke liye prepare karo
    Kokoro Hindi ko Roman script mein best samajhta hai
    """
    try:
        # Agar text already Roman/English hai
        if all(ord(c) < 128 for c in text):
            return text

        # Hindi Devanagari to Roman transliteration
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "indic-transliteration"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate

        roman_text = transliterate(
            text,
            sanscript.DEVANAGARI,
            sanscript.ITRANS
        )
        print(f"   🔤 Transliterated: {roman_text[:60]}...")
        return roman_text

    except Exception as e:
        print(f"   ⚠️ Transliteration failed: {e}. Using original.")
        return text

# ============================================================
# KOKORO VOICE GENERATOR
# ============================================================
def generate_voice_kokoro(scene_id, text):
    """
    Kokoro TTS se voice generate karo
    Male energetic Hindi voice
    """
    out_path = os.path.join(VOICE_DIR, f"voice_{scene_id}.wav")
    mp3_path = os.path.join(VOICE_DIR, f"voice_{scene_id}.mp3")

    # Pehle se bana hai toh skip
    if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1000:
        print(f"⏭️  Scene {scene_id} already exists. Skipping.")
        return mp3_path

    try:
        from kokoro_onnx import Kokoro
        import soundfile as sf
        import numpy as np

        print(f"🎙️  Generating voice for Scene {scene_id}...")

        # Kokoro initialize karo
        kokoro = Kokoro("kokoro-v0_19.onnx", "voices.bin")

        # Text prepare karo
        prepared_text = prepare_hindi_text(text)

        # Voice generate karo
        # am_michael = energetic male voice
        samples, sample_rate = kokoro.create(
            prepared_text,
            voice="am_michael",   # Energetic Male
            speed=1.1,            # Thoda fast - energetic feel
            lang="en-us"
        )

        # WAV save karo
        sf.write(out_path, samples, sample_rate)

        # WAV to MP3 convert karo
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", out_path,
                "-codec:a", "libmp3lame",
                "-qscale:a", "2",
                mp3_path
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # WAV delete karo
        if os.path.exists(out_path):
            os.remove(out_path)

        size = os.path.getsize(mp3_path)
        print(f"✅ Scene {scene_id} voice ready! ({size} bytes)")
        return mp3_path

    except Exception as e:
        print(f"❌ Kokoro failed for Scene {scene_id}: {e}")
        return None

# ============================================================
# KOKORO MODEL DOWNLOADER
# ============================================================
def download_kokoro_models():
    """
    Kokoro ke models download karo
    Sirf pehli baar download hoga
    """
    models = {
        "kokoro-v0_19.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx",
        "voices.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"
    }

    for filename, url in models.items():
        if os.path.exists(filename):
            print(f"✅ {filename} already exists!")
            continue

        print(f"📥 Downloading {filename}...")
        try:
            response = requests.get(url, stream=True, timeout=120)
            total    = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = int(downloaded * 100 / total)
                        if pct % 20 == 0:
                            print(f"   📊 {pct}% downloaded...")

            print(f"✅ {filename} downloaded!")

        except Exception as e:
            print(f"❌ Download failed for {filename}: {e}")
            return False

    return True

# ============================================================
# NARRATION EXTRACTOR
# ============================================================
def extract_narrations():
    """
    prompts.txt se Hindi narration part nikalo
    Format: visual_prompt | hindi_narration
    """
    if not os.path.exists(PROMPT_FILE):
        print(f"❌ {PROMPT_FILE} not found!")
        sys.exit(1)

    narrations = {}
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        if "|" in line:
            parts      = line.split("|", 1)
            hindi_text = parts[1].strip()
            if hindi_text:
                narrations[idx] = hindi_text
        else:
            narrations[idx] = line

    print(f"📝 {len(narrations)} narration scenes extracted!")

    # Debug
    for k, v in list(narrations.items())[:2]:
        print(f"   Scene {k}: {v[:60]}...")

    return narrations

# ============================================================
# AUDIO DURATION
# ============================================================
def get_audio_duration(audio_path):
    """
    Audio duration nikalo ffprobe se
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                audio_path
            ],
            capture_output=True,
            text=True
        )
        duration = float(result.stdout.strip())
        return round(duration, 2)
    except:
        return 4.0

# ============================================================
# TIMING MAP
# ============================================================
def create_timing_map(voice_files):
    """
    Har scene ki audio duration save karo
    process_videos.py use karega sync ke liye
    """
    timing_map = {}

    for scene_id, voice_path in voice_files.items():
        if voice_path and os.path.exists(voice_path):
            duration = get_audio_duration(voice_path)
            timing_map[str(scene_id)] = {
                "voice_path": voice_path,
                "duration_sec": duration
            }
            print(f"   ⏱️  Scene {scene_id}: {duration}s")
        else:
            timing_map[str(scene_id)] = {
                "voice_path": None,
                "duration_sec": 5.0
            }

    # Save karo
    with open("timing_map.json", "w", encoding="utf-8") as f:
        json.dump(timing_map, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Timing map saved!")
    return timing_map

# ============================================================
# MAIN
# ============================================================
def main():
    print("\n" + "="*50)
    print("🎙️  KOKORO TTS - FREE HINDI VOICE GENERATOR")
    print("="*50 + "\n")

    # Step 1: Install karo
    if not install_kokoro():
        print("❌ Installation failed!")
        sys.exit(1)

    # Step 2: Models download karo
    print("\n📥 Checking Kokoro models...")
    if not download_kokoro_models():
        print("❌ Model download failed!")
        sys.exit(1)

    # Step 3: Narrations nikalo
    print("\n📝 Extracting narrations...")
    narrations = extract_narrations()

    if not narrations:
        print("❌ Koi narration nahi mila!")
        sys.exit(1)

    # Step 4: Har scene ke liye voice banao
    print(f"\n🚀 Generating voices for {len(narrations)} scenes...\n")
    voice_files = {}

    for scene_id, hindi_text in narrations.items():
        print(f"\n--- Scene {scene_id} ---")
        print(f"📝 Text: {hindi_text[:80]}...")

        voice_path = generate_voice_kokoro(
            scene_id = scene_id,
            text     = hindi_text
        )

        voice_files[scene_id] = voice_path
        time.sleep(0.3)

    # Step 5: Timing map banao
    print("\n⏱️  Creating timing map...")
    timing_map = create_timing_map(voice_files)

    # Summary
    success = sum(1 for v in voice_files.values() if v)
    failed  = len(voice_files) - success

    print("\n" + "="*50)
    print(f"🎉 VOICE GENERATION COMPLETE!")
    print(f"   ✅ Success : {success} scenes")
    print(f"   ❌ Failed  : {failed} scenes")
    print(f"   📁 Saved   : {VOICE_DIR}/")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
