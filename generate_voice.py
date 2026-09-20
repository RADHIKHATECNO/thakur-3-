import os
import sys
import json
import time
import requests

# ============================================================
# CONFIG
# ============================================================
PROMPT_FILE  = "prompts.txt"
CONFIG_FILE  = "video_config.json"
VOICE_DIR    = "scene_voices"
os.makedirs(VOICE_DIR, exist_ok=True)

# ============================================================
# ELEVENLABS MULTI-KEY MANAGER
# ============================================================
def get_api_keys():
    """
    Secrets se saari API keys lo
    ELEVENLABS_API_KEY_1, _2, _3, _4, _5, _6
    """
    keys = []
    for i in range(1, 7):
        key = os.getenv(f"ELEVENLABS_API_KEY_{i}", "").strip()
        if key:
            keys.append(key)

    if not keys:
        print("❌ ERROR: Koi bhi ElevenLabs API key nahi mili!")
        sys.exit(1)

    print(f"✅ {len(keys)} ElevenLabs API key(s) mili!")
    return keys

def check_credits(api_key):
    """
    Check karo is key mein credits hain ya nahi
    """
    try:
        url = "https://api.elevenlabs.io/v1/user/subscription"
        headers = {"xi-api-key": api_key}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            used      = data.get("character_count", 0)
            limit     = data.get("character_limit", 0)
            remaining = limit - used
            print(f"   💳 Credits remaining: {remaining}/{limit}")
            return remaining > 100  # 100 se zyada hone chahiye
        else:
            print(f"   ⚠️ Credit check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ⚠️ Credit check error: {e}")
        return False

def get_working_key(api_keys):
    """
    Saari keys check karo, jo kaam kare woh do
    Auto switch karta hai
    """
    for idx, key in enumerate(api_keys, 1):
        print(f"\n🔑 Checking API Key {idx}...")
        if check_credits(key):
            print(f"✅ Key {idx} is working! Using this key.")
            return key
        else:
            print(f"❌ Key {idx} has no credits. Trying next...")

    print("❌ CRITICAL: Saari API keys ke credits khatam ho gaye!")
    sys.exit(1)

# ============================================================
# VOICE GENERATOR
# ============================================================
def generate_voice_for_scene(
    scene_id,
    hindi_text,
    api_key,
    voice_id,
    api_keys
):
    """
    Ek scene ke liye Hindi voice generate karo
    Agar key fail ho toh auto switch karo
    """
    out_path = os.path.join(VOICE_DIR, f"voice_{scene_id}.mp3")

    # Pehle se bani hai toh skip
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
        print(f"⏭️  Scene {scene_id} voice already exists. Skipping.")
        return out_path, api_key

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    payload = {
        "text": hindi_text,
        "model_id": "eleven_multilingual_v2",  # Hindi support ke liye best model
        "voice_settings": {
            "stability": 0.35,        # Energetic ke liye low stability
            "similarity_boost": 0.80,
            "style": 0.70,            # Expressive style
            "use_speaker_boost": True  # Energetic boost
        }
    }

    max_retries = 3
    current_key = api_key
    key_index   = api_keys.index(api_key)

    for attempt in range(1, max_retries + 1):
        print(f"🎙️  Scene {scene_id} - Attempt {attempt}/{max_retries}")

        try:
            headers = {
                "xi-api-key": current_key,
                "Content-Type": "application/json"
            }
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )

            # ✅ Success
            if response.status_code == 200:
                with open(out_path, "wb") as f:
                    f.write(response.content)
                print(f"✅ Scene {scene_id} voice generated! ({len(response.content)} bytes)")
                return out_path, current_key

            # 💳 Credits khatam - next key try karo
            elif response.status_code in [401, 429]:
                print(f"⚠️  Key exhausted (Status {response.status_code})! Switching to next key...")
                key_index += 1
                if key_index < len(api_keys):
                    current_key = api_keys[key_index]
                    print(f"🔑 Switched to Key {key_index + 1}")
                    time.sleep(2)
                else:
                    print("❌ Saari keys khatam ho gayi!")
                    sys.exit(1)

            # ⚠️ Server error - retry
            elif response.status_code >= 500:
                print(f"⚠️  Server error {response.status_code}. Retrying in 5 sec...")
                time.sleep(5)

            else:
                print(f"⚠️  Unexpected status {response.status_code}: {response.text[:100]}")
                time.sleep(3)

        except requests.exceptions.Timeout:
            print(f"⚠️  Timeout on attempt {attempt}. Retrying...")
            time.sleep(5)

        except Exception as e:
            print(f"⚠️  Error: {e}. Retrying...")
            time.sleep(3)

    print(f"❌ Scene {scene_id} voice failed after {max_retries} attempts!")
    return None, current_key

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
        if "|" in line:
            parts = line.split("|", 1)
            hindi_text = parts[1].strip()
            if hindi_text:
                narrations[idx] = hindi_text
        elif line:
            narrations[idx] = line  # Fallback

    print(f"📝 {len(narrations)} narration scenes extracted!")
    return narrations

# ============================================================
# DURATION CALCULATOR
# ============================================================
def get_audio_duration(audio_path):
    """
    Audio file ki duration seconds mein nikalo
    FFprobe use karta hai
    """
    try:
        import subprocess
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                audio_path
            ],
            capture_output=True, text=True
        )
        duration = float(result.stdout.strip())
        return round(duration, 2)
    except:
        return 4.0  # Default fallback

# ============================================================
# TIMING MAP GENERATOR
# ============================================================
def create_timing_map(voice_files):
    """
    Har scene ki audio duration save karo
    Yeh process_videos.py use karega sync ke liye
    """
    timing_map = {}

    for scene_id, voice_path in voice_files.items():
        if voice_path and os.path.exists(voice_path):
            duration = get_audio_duration(voice_path)
            timing_map[scene_id] = {
                "voice_path": voice_path,
                "duration_sec": duration
            }
            print(f"   Scene {scene_id}: {duration}s")
        else:
            timing_map[scene_id] = {
                "voice_path": None,
                "duration_sec": 5.0  # Default
            }

    # Save karo
    with open("timing_map.json", "w", encoding="utf-8") as f:
        json.dump(timing_map, f, indent=2)

    print(f"\n✅ Timing map saved! Total scenes: {len(timing_map)}")
    return timing_map

# ============================================================
# MAIN
# ============================================================
def main():
    print("\n" + "="*50)
    print("🎙️  ELEVENLABS HINDI VOICE GENERATOR")
    print("="*50 + "\n")

    # Config load karo
    voice_id = os.getenv(
        "ELEVENLABS_VOICE_ID",
        "pNInz6obpgDQGcFmaJgB"  # Default: Adam (Energetic Male)
    )
    print(f"🎤 Voice ID: {voice_id}")

    # API Keys lo
    api_keys = get_api_keys()

    # Working key dhundo
    current_key = get_working_key(api_keys)

    # Narrations nikalo
    narrations = extract_narrations()

    if not narrations:
        print("❌ Koi narration nahi mila!")
        sys.exit(1)

    # Har scene ke liye voice banao
    print(f"\n🚀 Generating voices for {len(narrations)} scenes...\n")
    voice_files = {}

    for scene_id, hindi_text in narrations.items():
        print(f"\n--- Scene {scene_id} ---")
        print(f"📝 Text: {hindi_text[:60]}...")

        voice_path, current_key = generate_voice_for_scene(
            scene_id=scene_id,
            hindi_text=hindi_text,
            api_key=current_key,
            voice_id=voice_id,
            api_keys=api_keys
        )
        voice_files[scene_id] = voice_path
        time.sleep(0.5)  # Rate limit se bachne ke liye

    # Timing map banao
    print("\n⏱️  Creating timing map...")
    timing_map = create_timing_map(voice_files)

    # Summary
    success = sum(1 for v in voice_files.values() if v)
    failed  = len(voice_files) - success

    print("\n" + "="*50)
    print(f"🎉 VOICE GENERATION COMPLETE!")
    print(f"   ✅ Success : {success} scenes")
    print(f"   ❌ Failed  : {failed} scenes")
    print(f"   📁 Saved in: {VOICE_DIR}/")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
