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
VOICE_DIR   = "scene_voices"
os.makedirs(VOICE_DIR, exist_ok=True)

# ============================================================
# NARRATION EXTRACTOR
# ============================================================
def extract_narrations():
    """
    prompts.txt se SIRF Hindi narration nikalo
    Format: NARRATION >> IMAGE_PROMPT >> VIDEO_PROMPT
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

        if ">>" in line:
            # NARRATION >> IMAGE >> VIDEO
            parts          = line.split(">>")
            hindi_narration = parts[0].strip()
            narrations[idx] = hindi_narration
        elif "|" in line:
            # Old format fallback
            parts          = line.split("|")
            hindi_narration = parts[1].strip() if len(parts) > 1 else parts[0].strip()
            narrations[idx] = hindi_narration
        else:
            narrations[idx] = line

    print(f"📝 {len(narrations)} narrations extracted!")
    for k, v in list(narrations.items())[:2]:
        print(f"   Scene {k}: {v[:70]}...")

    return narrations

# ============================================================
# KOKORO INSTALLER
# ============================================================
def install_kokoro():
    print("📦 Installing Kokoro TTS...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "kokoro-onnx", "soundfile", "numpy"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ Kokoro installed!")
        return True
    except Exception as e:
        print(f"❌ Install failed: {e}")
        return False

# ============================================================
# MODEL DOWNLOADER
# ============================================================
def download_kokoro_models():
    models = {
        "kokoro-v0_19.onnx": (
            "https://github.com/thewh1teagle/kokoro-onnx/"
            "releases/download/model-files/kokoro-v0_19.onnx"
        ),
        "voices.bin": (
            "https://github.com/thewh1teagle/kokoro-onnx/"
            "releases/download/model-files/voices.bin"
        )
    }

    for filename, url in models.items():
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"✅ {filename} exists ({size} bytes)")
            continue

        print(f"📥 Downloading {filename}...")
        try:
            response   = requests.get(url, stream=True, timeout=300)
            total      = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = int(downloaded * 100 / total)
                        if pct % 25 == 0:
                            print(f"   {pct}%...")

            print(f"✅ {filename} downloaded!")
        except Exception as e:
            print(f"❌ Failed: {e}")
            return False

    return True

# ============================================================
# HINDI TEXT PREPARER
# ============================================================
def prepare_hindi_text(text):
    """
    Hindi ko Roman mein convert karo
    Kokoro ke liye
    """
    try:
        # Check if already Roman
        hindi_chars = sum(
            1 for c in text
            if '\u0900' <= c <= '\u097F'
        )

        if hindi_chars == 0:
            return text  # Already Roman

        # Install transliteration
        subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "indic-transliteration"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate

        roman = transliterate(
            text,
            sanscript.DEVANAGARI,
            sanscript.ITRANS
        )

        # Fix common issues
        roman = roman.replace("  ", " ").strip()
        print(f"   🔤 Hindi→Roman: {roman[:60]}...")
        return roman

    except Exception as e:
        print(f"   ⚠️ Transliteration failed: {e}")
        return text

# ============================================================
# VOICE GENERATOR
# ============================================================
def generate_voice_kokoro(scene_id, hindi_text):
    """
    Kokoro TTS se Hindi voice generate karo
    """
    wav_path = os.path.join(VOICE_DIR, f"voice_{scene_id}.wav")
    mp3_path = os.path.join(VOICE_DIR, f"voice_{scene_id}.mp3")

    # Already exists?
    if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1000:
        print(f"⏭️  Scene {scene_id} already done!")
        return mp3_path

    try:
        from kokoro_onnx import Kokoro
        import soundfile as sf

        print(f"🎙️  Scene {scene_id} generating...")

        # Text prepare karo
        roman_text = prepare_hindi_text(hindi_text)

        # Kokoro init
        kokoro = Kokoro("kokoro-v0_19.onnx", "voices.bin")

        # Voice generate
        samples, sample_rate = kokoro.create(
            roman_text,
            voice="am_michael",  # Energetic Male
            speed=1.15,          # Thoda fast energetic
            lang="en-us"
        )

        # WAV save
        sf.write(wav_path, samples, sample_rate)

        # MP3 convert
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", wav_path,
                "-codec:a", "libmp3lame",
                "-qscale:a", "2",
                "-ar", "44100",
                mp3_path
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # WAV delete
        if os.path.exists(wav_path):
            os.remove(wav_path)

        size = os.path.getsize(mp3_path)
        print(f"✅ Scene {scene_id} done! ({size} bytes)")
        return mp3_path

    except Exception as e:
        print(f"❌ Scene {scene_id} failed: {e}")
        return None

# ============================================================
# AUDIO DURATION
# ============================================================
def get_audio_duration(path):
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0", path
            ],
            capture_output=True, text=True
        )
        return round(float(result.stdout.strip()), 2)
    except:
        return 4.0

# ============================================================
# TIMING MAP
# ============================================================
def create_timing_map(voice_files):
    timing_map = {}

    for scene_id, voice_path in voice_files.items():
        if voice_path and os.path.exists(voice_path):
            dur = get_audio_duration(voice_path)
            timing_map[str(scene_id)] = {
                "voice_path"  : voice_path,
                "duration_sec": dur
            }
            print(f"   ⏱️  Scene {scene_id}: {dur}s")
        else:
            timing_map[str(scene_id)] = {
                "voice_path"  : None,
                "duration_sec": 5.0
            }

    with open("timing_map.json", "w", encoding="utf-8") as f:
        json.dump(timing_map, f, indent=2, ensure_ascii=False)

    print("✅ Timing map saved!")
    return timing_map

# ============================================================
# MAIN
# ============================================================
def main():
    print("\n" + "="*50)
    print("🎙️  KOKORO TTS - FREE HINDI VOICE")
    print("="*50 + "\n")

    # Install
    if not install_kokoro():
        sys.exit(1)

    # Models download
    print("\n📥 Checking models...")
    if not download_kokoro_models():
        sys.exit(1)

    # Narrations nikalo
    print("\n📝 Extracting Hindi narrations...")
    narrations = extract_narrations()

    if not narrations:
        print("❌ No narrations found!")
        sys.exit(1)

    # Voices banao
    print(f"\n🚀 Generating {len(narrations)} voices...\n")
    voice_files = {}

    for scene_id, hindi_text in narrations.items():
        print(f"\n--- Scene {scene_id} ---")
        print(f"📝 Hindi: {hindi_text[:70]}...")

        voice_path = generate_voice_kokoro(scene_id, hindi_text)
        voice_files[scene_id] = voice_path
        time.sleep(0.3)

    # Timing map
    print("\n⏱️  Creating timing map...")
    create_timing_map(voice_files)

    # Summary
    success = sum(1 for v in voice_files.values() if v)
    failed  = len(voice_files) - success

    print("\n" + "="*50)
    print(f"🎉 DONE!")
    print(f"   ✅ Success: {success}")
    print(f"   ❌ Failed : {failed}")
    print("="*50)

if __name__ == "__main__":
    main()
