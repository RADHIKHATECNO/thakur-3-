import os
import requests
import json

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/"
# Use a specific voice ID (e.g., 'pNInz6obpgDQGcFmaJgB' - Adam)
VOICE_ID = "pNInz6obpgDQGcFmaJgB" 
INPUT_FILE = "voice_script.txt"
OUTPUT_FILE = "voiceover.wav"

def get_api_keys():
    raw = os.getenv("ELEVENLABS_API_KEYS", "")
    return [k.strip() for k in raw.split(",") if k.strip()]

def generate():
    if not os.path.exists(INPUT_FILE):
        print("❌ Error: voice_script.txt missing!")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    keys = get_api_keys()
    if not keys:
        print("❌ Error: No ELEVENLABS_API_KEYS provided!")
        return

    for i, key in enumerate(keys):
        print(f"🔄 Trying Key {i+1}/{len(keys)}...")
        headers = {"xi-api-key": key, "Content-Type": "application/json"}
        data = {"text": text, "model_id": "eleven_multilingual_v2", "voice_id": VOICE_ID}
        
        try:
            resp = requests.post(f"{ELEVENLABS_URL}{VOICE_ID}", json=data, headers=headers, timeout=60)
            if resp.status_code == 200:
                with open(OUTPUT_FILE, "wb") as f: f.write(resp.content)
                print("✅ Voice Generated Successfully!")
                return
            elif resp.status_code == 429:
                print("⚠️ Quota exceeded. Trying next key.")
                continue
            else:
                print(f"⚠️ Error {resp.status_code}: {resp.text}")
                continue
        except Exception:
            print("⚠️ Connection Error. Trying next key.")
            continue

    print("❌ Failed to generate voice with all keys.")

if __name__ == "__main__":
    generate()
