import os
import json
import time
import sys
from openai import OpenAI

XKIRO_API_KEY = os.getenv("XKIRO_API_KEY")
if not XKIRO_API_KEY: 
    print("❌ ERROR: XKIRO_API_KEY missing!")
    sys.exit(1)

client = OpenAI(
    api_key=XKIRO_API_KEY, 
    base_url="https://api.xkiro.com/v1"
)

def load_client_config():
    with open("client_setup.json", "r", encoding="utf-8") as f: 
        return json.load(f)

def get_dynamic_models():
    print("🔍 Fetching active models from xKiro...")
    try:
        models_data = client.models.list()
        all_models = [m.id for m in models_data.data]
        best_keywords = ["qwen", "deepseek", "flash", "gpt", "llama"]
        prioritized = [m for k in best_keywords for m in all_models if k in m.lower()]
        if not prioritized: 
            return all_models[:10]
        return list(dict.fromkeys(prioritized))[:15]
    except Exception as e:
        print(f"⚠️ Auto-fetch failed: {e}. Using safe fallbacks.")
        return ["qwen-2.5-72b", "deepseek-chat", "gpt-4o-mini"]

def generate_cinematic_json(config):
    total_scenes = max(4, int(config["duration_seconds"] / 4))
    
    # Strictly defining instructions to avoid bloated prompts that exceed Bing's 450 limit
    system_prompt = f"""You are a master cinematic video director. Write a {total_scenes}-scene story.
Output ONLY a raw JSON array. No markdown, no "```json", no explanatory text.
Required JSON schema format:
[
  {{
    "scene": 1,
    "narration": "Hindi/Hinglish dialogue line (max 10 words)",
    "image_prompt": "Extremely concise english visual description (MAX 250 CHARACTERS)",
    "sfx": "wind_howl",
    "camera": "smooth_pan"
  }}
]
CAMERA OPTIONS: [fast_zoom, zoom_out, shake, smooth_pan]
PROMPT RULES:
1. Every "image_prompt" must include this exact anchor: '{config.get('character_anchor', '')}'.
2. Every scene must include: '{config.get('art_style', '')}'.
3. Keep the prompt UNDER 300 characters combined! Make it short and punchy so the image generator doesn't fail.
"""

    user_prompt = f"Write a complete logical story with a clear start, middle, climax and end. Topic: {config.get('topic')}"

    print(f"🎬 Directing {total_scenes} well-paced scenes...")
    
    models = get_dynamic_models()
    for model in models:
        print(f"🔄 Trying model: {model}...")
        try:
            response = client.chat.completions.create(
                model=model, 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ], 
                temperature=0.7
            )
            output = response.choices[0].message.content.strip()
            
            # 🔥 Stripping formatting tags
            if output.startswith("```json"): output = output[7:]
            if output.startswith("```"): output = output[3:]
            if output.endswith("```"): output = output[:-3]
            output = output.strip()
                
            script_data = json.loads(output)
            if isinstance(script_data, dict) and "scenes" in script_data: 
                script_data = script_data["scenes"]
                
            if isinstance(script_data, list) and len(script_data) > 0:
                with open("script_data.json", "w", encoding="utf-8") as f:
                    json.dump(script_data, f, indent=4, ensure_ascii=False)
                print(f"✅ Success! Generated {len(script_data)} scenes using {model}.")
                return True
        except Exception as e:
            print(f"⚠️ Failed with {model}: {str(e)[:100]}... Trying next.")
            time.sleep(2)
            
    return False

if __name__ == "__main__":
    config = load_client_config()
    if generate_cinematic_json(config): 
        print("🚀 JSON Script Generated and Saved!")
    else:
        print("❌ CRITICAL ERROR: All models failed to write script. Stopping Action.")
        sys.exit(1)
