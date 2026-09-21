import os
import json
import time
from openai import OpenAI

# 1. API Setup (xKiro API Key GitHub Secrets se aayegi)
XKIRO_API_KEY = os.getenv("XKIRO_API_KEY")

if not XKIRO_API_KEY:
    print("❌ ERROR: XKIRO_API_KEY nahi mili! Kripya GitHub Secrets check karein.")
    exit(1)

# xKiro ka Base URL
client = OpenAI(
    api_key=XKIRO_API_KEY,
    base_url="https://api.xkiro.com/v1" 
)

# 38 Free Models mein se Best Fallback Array
MODELS = [
    "qwen-2.5-72b-instruct",  # Fast & Smart for JSON
    "deepseek-coder",         # Great fallback for logic
    "llama-3.1-70b-instruct"  # Backup
]

def load_client_config():
    with open("client_setup.json", "r", encoding="utf-8") as f:
        return json.load(f)

def generate_cinematic_json(config):
    # Duration ke hisaab se scenes calculate karna (approx 4 seconds per scene)
    total_scenes = max(5, int(config["duration_seconds"] / 4))
    
    system_prompt = """You are a Hollywood-level YouTube Video Director. 
Your ONLY job is to return a strict, valid JSON array. DO NOT output any markdown, intro, or outro text. ONLY JSON.
Format required:
[
  {
    "scene": 1,
    "narration": "Hindi/Hinglish voiceover dialogue here (max 10 words)",
    "image_prompt": "Highly detailed DALL-E prompt here",
    "sfx": "One word sound effect name (e.g., thunder, whoosh, heartbeat, horror_drone, wind)"
  }
]"""

    user_prompt = f"""
Create a highly engaging script for a {config['video_format']} format video.
Topic: {config['topic']}
Total Scenes Required: EXACTLY {total_scenes}
Art Style for all images: {config['art_style']}

CRITICAL INSTRUCTION FOR IMAGES:
Every single "image_prompt" MUST include this exact character description to maintain consistency: 
"{config['character_anchor']}"

Make the first scene a high-suspense HOOK!
"""

    print(f"🎬 Action! Directing {total_scenes} scenes for {config['client_name']}...")

    for model in MODELS:
        print(f"🔄 Trying model: {model}...")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"} # Forces strict JSON
            )
            
            output_text = response.choices[0].message.content.strip()
            
            # Verify if it's a valid JSON
            script_data = json.loads(output_text)
            
            # Check if JSON has 'scenes' array or is an array itself
            if isinstance(script_data, dict) and "scenes" in script_data:
                script_data = script_data["scenes"]
                
            print(f"✅ Success! Generated {len(script_data)} scenes using {model}.")
            
            # Save the brain output to a file for the next scripts
            with open("script_data.json", "w", encoding="utf-8") as f:
                json.dump(script_data, f, indent=4, ensure_ascii=False)
                
            return True

        except Exception as e:
            print(f"⚠️ Model {model} failed: {e}. Retrying in 5 seconds...")
            time.sleep(5) # API Rate limit se bachne ke liye

    print("❌ All xKiro models failed. Please check API limit or network.")
    return False

if __name__ == "__main__":
    if not os.path.exists("client_setup.json"):
        print("❌ ERROR: client_setup.json nahi mili!")
        exit(1)
        
    config = load_client_config()
    success = generate_cinematic_json(config)
    
    if success:
        print("🚀 JSON Script successfully saved to script_data.json!")
    else:
        exit(1)
