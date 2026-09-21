import os
import json
import time
from openai import OpenAI

XKIRO_API_KEY = os.getenv("XKIRO_API_KEY")
if not XKIRO_API_KEY: exit(1)

client = OpenAI(api_key=XKIRO_API_KEY, base_url="https://api.xkiro.com/v1")

def load_client_config():
    with open("client_setup.json", "r", encoding="utf-8") as f: return json.load(f)

def get_dynamic_models():
    return ["qwen-2.5-72b", "deepseek-chat", "gpt-4o-mini"] # Failsafe fast models

def generate_cinematic_json(config):
    total_scenes = max(4, int(config["duration_seconds"] / 4))
    
    # 🔥 AI DIRECTS THE CAMERA NOW!
    system_prompt = f"""You are a Hollywood YouTube Director.
Write a {total_scenes}-scene story. Return a strict JSON array.
Format required:
[
  {{
    "scene": 1,
    "narration": "Hindi/Hinglish dialogue (max 10 words)",
    "image_prompt": "Highly detailed prompt (MAX 350 CHARACTERS)",
    "sfx": "thunder",
    "camera": "Choose ONE: [fast_zoom, zoom_out, shake, smooth_pan]"
  }}
]
CAMERA RULES:
- If action is shocking/revealing: use 'fast_zoom'
- If showing a large landscape/spaceship: use 'zoom_out'
- If impact, fear, or explosion: use 'shake'
- Default calm scene: 'smooth_pan'

Keep image_prompts consistent with the anchor: '{config['character_anchor']}' and style: '{config['art_style']}'.
"""

    user_prompt = f"Topic: {config['topic']}"

    print(f"🎬 Directing {total_scenes} scenes with AI Camera Moves...")
    
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="qwen-2.5-72b", 
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], 
                temperature=0.7
            )
            output = response.choices[0].message.content.strip()
            if output.startswith("```json"): output = output[7:]
            if output.startswith("```"): output = output[3:]
            if output.endswith("```"): output = output[:-3]
                
            script_data = json.loads(output.strip())
            if isinstance(script_data, dict) and "scenes" in script_data: script_data = script_data["scenes"]
                
            if isinstance(script_data, list):
                with open("script_data.json", "w", encoding="utf-8") as f:
                    json.dump(script_data, f, indent=4, ensure_ascii=False)
                print("✅ Success! AI Camera Script generated.")
                return True
        except Exception as e:
            print(f"⚠️ Failed: {str(e)[:50]}")
            time.sleep(2)
            
    return False

if __name__ == "__main__":
    if generate_cinematic_json(load_client_config()): print("🚀 Script Saved!")
