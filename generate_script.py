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
    
    # 🔥 MAGIC FIX: Now AI only writes the action. We lock the character in Python!
    system_prompt = f"""You are a master Hollywood Film Director and After Effects VFX Expert.
Your job is to direct a highly intense and emotional {total_scenes}-scene short-form story based on the client's topic.

You must output ONLY a valid, raw JSON array containing the complete editing timeline. DO NOT output any markdown tags.

Required JSON Structure:
[
    {{
      "scene": 1,
      "narration": "Hindi/Hinglish dialogue here (max 8 words)",
      "action_only": "Concise English description of ONLY the background and what is happening (MAX 100 CHARACTERS). DO NOT describe the character's looks, just what they are doing.",
      "parallax": true,
      "camera": "Choose ONE: [fast_zoom, zoom_out, smooth_pan, shake]",
      "sfx": "Choose ONE: [whoosh, thunder_blast, heartbeat, metal_clang, horror_drone]",
      "sfx_delay_ms": 500,
      "vfx_effect": "Choose ONE: [white_flash, vignette_glow, none]"
    }}
]

STRICT EDITING RULES:
1. "parallax": Set to true ONLY if the character is clearly visible and doing an action.
2. "sfx_delay_ms": Define the exact delay in milliseconds when the sound effect should trigger.
3. Keep "action_only" under 100 characters!
"""

    user_prompt = f"Create the ultimate timeline script for: {config.get('topic')}"

    print(f"🎬 Directing {total_scenes} timeline scenes (With Hard-Locked Character Consistency)...")
    
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
            
            if output.startswith("```json"): output = output[7:]
            if output.startswith("```"): output = output[3:]
            if output.endswith("```"): output = output[:-3]
            output = output.strip()
                
            script_data = json.loads(output)
            
            if isinstance(script_data, dict) and "scenes" in script_data:
                script_data = script_data["scenes"]
                
            if isinstance(script_data, list) and len(script_data) > 0:
                
                # 🔥 THE UNBREAKABLE LOCK: Python injects identical style and character into every prompt!
                art_style = config.get("art_style", "")
                anchor = config.get("character_anchor", "")
                
                for scene in script_data:
                    action = scene.get("action_only", "standing still")
                    # DALL-E 3 will read this exact same prefix every single time!
                    scene["image_prompt"] = f"{art_style}. Character: {anchor}. Action and Scene: {action}"
                
                with open("script_data.json", "w", encoding="utf-8") as f:
                    json.dump(script_data, f, indent=4, ensure_ascii=False)
                print(f"✅ Success! Generated {len(script_data)} highly consistent scenes using {model}.")
                return True
                
        except Exception as e:
            print(f"⚠️ Failed with {model}: {str(e)[:100]}")
            time.sleep(2)
            
    return False

if __name__ == "__main__":
    config = load_client_config()
    if generate_cinematic_json(config): 
        print("🚀 Master Timeline JSON Saved with Perfect Consistency!")
    else:
        print("❌ CRITICAL ERROR: Script generation failed. Stopping pipeline.")
        sys.exit(1)
