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
    try:
        all_models = [m.id for m in client.models.list().data]
        best_keywords = ["qwen", "deepseek", "flash", "gpt", "llama"]
        prioritized = [m for k in best_keywords for m in all_models if k in m.lower()]
        return list(dict.fromkeys(prioritized))[:15]
    except:
        return ["qwen-2.5-72b", "deepseek-chat", "gpt-4o-mini"]

def generate_cinematic_json(config):
    total_scenes = max(5, int(config["duration_seconds"] / 4))
    
    # 🔥 YAHAN MAGIC HAI: AI ab animation bhi decide karega!
    system_prompt = """You are a Hollywood YouTube Director AND Animator. 
Return a strict JSON array. Format required:
[
  {
    "scene": 1,
    "narration": "Hindi/Hinglish dialogue (max 10 words)",
    "image_prompt": "Highly detailed DALL-E prompt",
    "sfx": "thunder",
    "animation": "Choose ONE based on story context: [fly_up, drive_forward, slide_left, slide_right, float_clouds, zoom_in]"
  }
]
RULES FOR ANIMATION:
- If character is jumping/flying to sky: use 'fly_up'
- If vehicle/character moving forward on road: use 'drive_forward'
- If character entering scene: use 'slide_left' or 'slide_right'
- If dreamy/sky scene: use 'float_clouds'
- Default: 'zoom_in'
"""

    user_prompt = f"Topic: {config['topic']}\nScenes: {total_scenes}\nArt Style: {config['art_style']}\nAnchor: {config['character_anchor']}"

    print(f"🎬 Directing {total_scenes} Context-Aware scenes...")
    for model in get_dynamic_models():
        print(f"🔄 Trying model: {model}...")
        try:
            response = client.chat.completions.create(model=model, messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.7)
            
            output = response.choices[0].message.content.strip()
            if output.startswith("```json"): output = output[7:]
            if output.startswith("```"): output = output[3:]
            if output.endswith("```"): output = output[:-3]
                
            script_data = json.loads(output.strip())
            if isinstance(script_data, dict) and "scenes" in script_data: script_data = script_data["scenes"]
                
            if isinstance(script_data, list):
                with open("script_data.json", "w", encoding="utf-8") as f:
                    json.dump(script_data, f, indent=4, ensure_ascii=False)
                print(f"✅ Success! AI Animator created {len(script_data)} scenes.")
                return True
        except Exception as e:
            print(f"⚠️ Failed: {str(e)[:50]}")
            time.sleep(2)
    return False

if __name__ == "__main__":
    if generate_cinematic_json(load_client_config()):
        print("🚀 Smart JSON Script Saved!")
    else: exit(1)
