import os
import sys
import requests
import time

api_keys_env = os.getenv("ELEVENLABS_KEYS", "")
API_KEYS = [k.strip() for k in api_keys_env.split(",") if k.strip()]

# 🎙️ Professional Hindi Voice IDs (ElevenLabs)
VOICE_ID = "pNInz6obpgDQGcFmaJcg"  # Adam - Best for stories

if not API_KEYS:
    print("⚠️ ELEVENLABS_KEYS not found. Skipping voice generation.")
    sys.exit(0)

def generate_audio(text, output_filename):
    for idx, key in enumerate(API_KEYS, 1):
        print(f"🎙️ Trying API Key {idx}/{len(API_KEYS)}: {key[:6]}***")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
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
                print(f"⚠️ Key {idx} error: {response.status_code} - {response.text[:100]}")
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
            print(f"🎬 Scene {idx}: {dialogue[:50]}...")
            output_file = f"scene_audio/voice_{idx}.mp3"
            if generate_audio(dialogue, output_file):
                success += 1
            time.sleep(0.5)
        else:
            print(f"⚠️ Scene {idx}: Missing dialogue part. Skipping.")

    print(f"🎉 Voice Generation Done! {success}/{len(lines)} voices created.")

if __name__ == "__main__":
    main()
