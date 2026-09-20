import os
import requests
import sys

# GitHub Secrets से APIs लेना
api_keys_env = os.getenv("ELEVENLABS_KEYS", "")
API_KEYS = [k.strip() for k in api_keys_env.split(",") if k.strip()]
VOICE_ID = "pNInz6obpgDQGcFmaJcg" # Adam Voice (Best for stories)

if not API_KEYS:
    print("❌ ERROR: ELEVENLABS_KEYS not found in secrets! Voiceover will be skipped.")
    sys.exit(0)

def generate_audio(text, output_filename):
    for key in API_KEYS:
        print(f"🎙️ Trying ElevenLabs API Key: {key[:5]}...***")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": key
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2", # यह हिंदी और इंग्लिश दोनों मस्त बोलता है
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }
        
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            with open(output_filename, 'wb') as f:
                f.write(response.content)
            print(f"✅ Voice generated successfully for: {output_filename}")
            return True
        else:
            print(f"⚠️ Key failed (Limit reached or error). Status: {response.status_code}")
            
    print("❌ All ElevenLabs API Keys Failed!")
    return False

def main():
    if not os.path.exists("prompts.txt"):
        print("❌ prompts.txt not found!")
        return

    os.makedirs("scene_audio", exist_ok=True)

    with open("prompts.txt", "r", encoding="utf-8") as f:
        for idx, line in enumerate(f.readlines(), 1):
            parts = line.strip().split("|")
            # 🔴 नया लॉजिक: तीसरा हिस्सा (index 2) वॉयसओवर डायलॉग है
            if len(parts) >= 3:
                dialogue = parts[2].strip()
                output_file = f"scene_audio/voice_{idx}.mp3"
                generate_audio(dialogue, output_file)
            else:
                print(f"⚠️ Line {idx} is missing the 3rd part (Dialogue). Skipped.")

if __name__ == "__main__":
    main()
