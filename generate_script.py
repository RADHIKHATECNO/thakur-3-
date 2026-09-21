import os
import json
import time
import sys
from openai import OpenAI

XKIRO_API_KEY = os.getenv("XKIRO_API_KEY")
if not XKIRO_API_KEY: 
    print("❌ ERROR: API Key Missing")
    sys.exit(1)

client = OpenAI(api_key=XKIRO_API_KEY, base_url="https://api.xkiro.com/v1")

def load_client_config():
    with open("client_setup.json", "r", encoding="utf-8") as f: 
        return json.load(f)

def get_dynamic_models():
    print("🔍 Searching for active models...")
    try:
        all_models = [m.id for m in client.models.list().data]
        best_keywords = ["qwen", "deepseek", "flash", "gpt", "llama"]
        prioritized = [m for k in best_keywords for m in all_models if k in m.lower()]
        
        if not prioritized: return all_models[:10]
        return list(dict.fromkeys(prioritized))[:15]
    except Exception as e:
        print(f"⚠️ Warning: Auto-fetch failed. Using default fallbacks.")
        return ["qwen-2.5-72b", "deepseek-chat", "gpt-4o-mini"]

def generate_cinematic_json(config):
    total_scenes = max(4, int(config["duration_seconds"] / 4))
    
    system_prompt = f"""You are a Hollywood YouTube Director.
Write a {total_scenes}-scene story. Return ONLY a strict JSON array.
Format required:
[
  {{
    "scene": 1,
    "narration": "Hindi/Hinglish dialogue (max 10 words)",
    "image_prompt": "Highly detailed DALL-E prompt (MAX 300 CHARACTERS)",
    "sfx": "thunder",
    "camera": "Choose ONE: [fast_zoom, zoom_out, shake, smooth_pan]"
  }}
]
CAMERA RULES:
- If action is shocking/revealing: use 'fast_zoom'
- If showing a large landscape/spaceship: use 'zoom_out'
- If impact, fear, or explosion: use 'shake'
- Default calm scene: 'smooth_pan'

Keep image_prompts consistent with the anchor: '{config.get('character_anchor', '')}' and style: '{config.get('art_style', '')}'.
"""

    user_prompt = f"Topic: {config.get('topic', 'A short amazing story')}"

    print(f"🎬 Directing {total_scenes} scenes with AI Camera Moves...")
    
    models = get_dynamic_models()
    for model in models:
        print(f"🔄 Trying model: {model}...")
        try:
            response = client.chat.completions.create(
                model=model, 
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], 
                temperature=0.7
            )
            output = response.choices[0].message.content.strip()
            if output.startswith("```json"): output = output[7:]
            if output.startswith("```"): output = output[3:]
            if output.endswith("```"): output = output[:-3]
                
            script_data = json.loads(output.strip())
            if isinstance(script_data, dict) and "scenes" in script_data: 
                script_data = script_data["scenes"]
                
            if isinstance(script_data, list) and len(script_data) > 0:
                with open("script_data.json", "w", encoding="utf-8") as f:
                    json.dump(script_data, f, indent=4, ensure_ascii=False)
                print(f"✅ Success! Generated {len(script_data)} scenes.")
                return True
        except Exception as e:
            print(f"⚠️ Failed with {model}: {str(e)[:50]}")
            time.sleep(2)
            
    return False

if __name__ == "__main__":
    if generate_cinematic_json(load_client_config()): 
        print("🚀 Script Saved Successfully!")
    else:
        # 🔥 YAHAN MAGIC HAI: Agar script nahi bani toh GitHub ko force-stop kar dega
        print("❌ CRITICAL ERROR: All models failed to generate script. Stopping pipeline.")
        sys.exit(1)
