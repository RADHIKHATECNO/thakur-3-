import os
import json
import time
from openai import OpenAI

XKIRO_API_KEY = os.getenv("XKIRO_API_KEY")
if not XKIRO_API_KEY: exit(1)

client = OpenAI(api_key=XKIRO_API_KEY, base_url="https://api.xkiro.com/v1")

def load_client_config():
    with open("client_setup.json", "r", encoding="utf-8") as f: 
        return json.load(f)

def get_dynamic_models():
    try:
        all_models = [m.id for m in client.models.list().data]
        best_keywords = ["qwen", "deepseek", "flash", "gpt", "llama"]
        prioritized = [m for k in best_keywords for m in all_models if k in m.lower()]
        return list(dict.fromkeys(prioritized))[:15]
    except:
        return ["qwen-2.5-72b", "deepseek-chat", "gpt-4o-mini"]

def generate_cinematic_json(config):
    # Calculate exact scenes based on duration (approx 4 seconds per scene)
    total_scenes = max(4, int(config["duration_seconds"] / 4))
    
    system_prompt = f"""You are a Master Hollywood Director and Story Writer.
Your job is to write a COMPLETE, logically paced story within EXACTLY {total_scenes} scenes.
Pacing Rules:
- Scene 1-2: Strong Hook / Beginning
- Middle Scenes: Build up the plot based on the topic
- Last 2 Scenes: Proper Climax and Conclusion.

Return ONLY a strict JSON array in this format:
[
  {{
    "scene": 1,
    "narration": "Hindi/Hinglish dialogue (max 10 words)",
    "image_prompt": "Highly detailed DALL-E prompt (MAX 350 CHARACTERS)",
    "sfx": "thunder",
    "animation": "Choose ONE: [fly_up, drive_forward, slide_left, slide_right, float_clouds, zoom_in]"
  }}
]

CRITICAL PROMPT RULES FOR CONSISTENCY (DO NOT IGNORE):
1. Keep the "image_prompt" UNDER 350 CHARACTERS to avoid crashing the image generator.
2. Every scene MUST include the exact art style: '{config['art_style']}'.
3. Every scene MUST include a short version of this character: '{config['character_anchor']}'.
4. If a specific object (like a spaceship, a magical pot, etc.) appears, describe it the exact same way in every scene it appears so it doesn't change shape.
5. Combine all these details concisely to stay under the character limit.
"""

    user_prompt = f"Topic to turn into a full story: {config['topic']}"

    print(f"🎬 Directing {total_scenes} well-paced scenes (Start to Finish)...")
    
    for model in get_dynamic_models():
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
                
            script_data = json.loads(output.strip())
            if isinstance(script_data, dict) and "scenes" in script_data: 
                script_data = script_data["scenes"]
                
            if isinstance(script_data, list):
                with open("script_data.json", "w", encoding="utf-8") as f:
                    json.dump(script_data, f, indent=4, ensure_ascii=False)
                print(f"✅ Success! AI Animator created a complete story in {len(script_data)} scenes.")
                return True
        except Exception as e:
            print(f"⚠️ Failed: {str(e)[:50]}")
            time.sleep(2)
            
    return False

if __name__ == "__main__":
    if generate_cinematic_json(load_client_config()):
        print("🚀 Smart JSON Script Saved!")
    else: 
        exit(1)
