import os
import requests
import sys

# GitHub Secrets से कॉमा (,) से अलग की हुई APIs लें
api_keys_env = os.getenv("ELEVENLABS_KEYS", "")
API_KEYS = [k.strip() for k in api_keys_env.split(",") if k.strip()]
VOICE_ID = "pNInz6obpgDQGcFmaJcg" # Adam (ElevenLabs default best voice)

if not API_KEYS:
    print("❌ ERROR: ELEVENLABS_KEYS not found in secrets!")
    sys.exit(1)

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
            "model_id": "eleven_multilingual_v2",
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

    with open("prompts.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

    os.makedirs("scene_audio", exist_ok=True)

    for idx, line in enumerate(lines, 1):
        if "|" in line:
            # | के बाद वाला हिस्सा डायलॉग है
            dialogue = line.split("|")[1].strip()
            # [Voice: ...] अगर लिखा है तो उसे साफ़ करें
            dialogue = dialogue.replace("[Voice:", "").replace("]", "").strip()
            
            output_file = f"scene_audio/voice_{idx}.mp3"
            generate_audio(dialogue, output_file)

if __name__ == "__main__":
    main()
