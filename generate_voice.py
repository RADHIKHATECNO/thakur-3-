import os
import sys
import requests
import time

api_keys_env = os.getenv("ELEVENLABS_KEYS", "")
API_KEYS = [k.strip() for k in api_keys_env.split(",") if k.strip()]

if not API_KEYS:
    print("⚠️ ELEVENLABS_KEYS not found. Skipping voice generation.")
    sys.exit(0)

def get_first_available_voice(api_key):
    """Account में जो पहली voice available हो, उसे use करो"""
    try:
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {"xi-api-key": api_key}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            voices = response.json().get("voices", [])
            if voices:
                voice_id = voices[0]["voice_id"]
                voice_name = voices[0]["name"]
                print(f"✅ Voice Found: {voice_name} (ID: {voice_id})")
                return voice_id
    except Exception as e:
        print(f"⚠️ Could not fetch voices: {e}")
    return None

def generate_audio(text, output_filename):
    for idx, key in enumerate(API_KEYS, 1):
        print(f"🎙️ Trying API Key {idx}/{len(API_KEYS)}: {key[:6]}***")

        # पहले account की available voice ID लो
        voice_id = get_first_available_voice(key)
        if not voice_id:
            print(f"⚠️ No voice found for Key {idx}. Trying next key...")
            continue

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": key
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.4,
                "similarity_boost": 0.80,
                "style": 0.5,
                "use_speaker_boost": True
            }
        }
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(output_filename, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Voice saved: {output_filename}")
                return True
            elif response.status_code == 429:
                print(f"⚠️ Key {idx} limit reached. Trying next key...")
                time.sleep(1)
            else:
                print(f"⚠️ Key {idx} error: {response.status_code} - {response.text[:150]}")
        except Exception as e:
            print(f"⚠️ Key {idx} exception: {e}")

    print(f"❌ All API Keys failed for: {output_filename}")
    return False

def main():
    print("🎙️ Starting Voice Generation...")

    if not os.path.exists("prompts.txt"):
        print("❌ prompts.txt not found!")
        sys.exit(1)

    os.makedirs("scene_audio", exist_ok=True)

    with open("prompts.txt", "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    print(f"📋 Total scenes to voice: {len(lines)}")
    success = 0

    for idx, line in enumerate(lines, 1):
        parts = line.split("|")
        if len(parts) >= 3:
            dialogue = parts[2].strip()
            print(f"\n🎬 Scene {idx}: {dialogue[:60]}...")
            output_file = f"scene_audio/voice_{idx}.mp3"
            if generate_audio(dialogue, output_file):
                success += 1
            time.sleep(1)
        else:
            print(f"⚠️ Scene {idx}: Missing dialogue. Skipping.")

    print(f"\n🎉 Done! {success}/{len(lines)} voices created successfully.")

if __name__ == "__main__":
    main()
