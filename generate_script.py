import os
import json
import time
from openai import OpenAI

# 1. API Setup
XKIRO_API_KEY = os.getenv("XKIRO_API_KEY")

if not XKIRO_API_KEY:
    print("❌ ERROR: XKIRO_API_KEY nahi mili! Kripya GitHub Secrets check karein.")
    exit(1)

client = OpenAI(
    api_key=XKIRO_API_KEY,
    base_url="https://api.xkiro.com/v1" 
)

def load_client_config():
    with open("client_setup.json", "r", encoding="utf-8") as f:
        return json.load(f)

# 🔥 THE MAGIC: Auto-Fetch Live Models!
def get_dynamic_models():
    print("🔍 Scanning xKiro API for live free models...")
    try:
        models_data = client.models.list()
        all_models = [m.id for m in models_data.data]
        print(f"✅ Found {len(all_models)} active models right now!")
        
        # Qwen aur DeepSeek JSON ke liye best hote hain, toh unhe priority denge
        best_keywords = ["qwen", "deepseek", "flash", "claude", "gpt", "llama"]
        prioritized = []
        
        for keyword in best_keywords:
            for m in all_models:
                if keyword in m.lower() and m not in prioritized:
                    prioritized.append(m)
                    
        # Baaki bache models bhi add kar do
        for m in all_models:
            if m not in prioritized:
                prioritized.append(m)
                
        return prioritized[:15] # Top 15 live models nikal liye
        
    except Exception as e:
        print(f"⚠️ Warning: Auto-fetch failed ({e}). Using smart fallbacks.")
        # Agar list fetch fail hui, toh ye universal names try karega
        return ["qwen-2.5-72b", "deepseek-chat", "gpt-4o-mini", "llama-3.1-70b"]

def generate_cinematic_json(config):
    total_scenes = max(5, int(config["duration_seconds"] / 4))
    
    system_prompt = """You are a Hollywood-level YouTube Video Director. 
Your ONLY job is to return a strict, valid JSON array. DO NOT output any markdown like ```json, intro, or outro text. ONLY raw JSON.
Format required exactly like this:
[
  {
    "scene": 1,
    "narration": "Hindi/Hinglish voiceover dialogue here (max 10 words)",
    "image_prompt": "Highly detailed DALL-E prompt here",
    "sfx": "thunder"
  }
]"""

    user_prompt = f"""
Create a highly engaging script for a {config['video_format']} format video.
Topic: {config['topic']}
Total Scenes Required: EXACTLY {total_scenes}
Art Style for all images: {config['art_style']}

CRITICAL INSTRUCTION FOR IMAGES:
Every single "image_prompt" MUST include this exact character description: "{config['character_anchor']}"
"""

    print(f"🎬 Action! Directing {total_scenes} scenes for {config['client_name']}...")
    
    # 🔴 Naya Logic: Sirf live models ko try karega
    dynamic_models = get_dynamic_models()

    for model in dynamic_models:
        print(f"\n🔄 Trying model: {model}...")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            
            output_text = response.choices[0].message.content.strip()
            
            # 🔥 Auto Markdown Cleaner (Agar AI ne galti se ```json laga diya toh use hata dega)
            if output_text.startswith("```json"):
                output_text = output_text[7:]
            if output_text.startswith("```"):
                output_text = output_text[3:]
            if output_text.endswith("```"):
                output_text = output_text[:-3]
                
            output_text = output_text.strip()
            
            # JSON validation
            script_data = json.loads(output_text)
            
            # Fix if AI wraps it inside "scenes" dictionary
            if isinstance(script_data, dict) and "scenes" in script_data:
                script_data = script_data["scenes"]
                
            if isinstance(script_data, list) and len(script_data) > 0:
                print(f"✅ Success! Generated {len(script_data)} scenes using {model}!")
                
                with open("script_data.json", "w", encoding="utf-8") as f:
                    json.dump(script_data, f, indent=4, ensure_ascii=False)
                    
                return True
            else:
                print("⚠️ Invalid JSON output format. Trying next model...")

        except Exception as e:
            # Agar fail hua toh error limit print karke agle model par chala jayega
            print(f"⚠️ Model Failed: {str(e)[:100]}... Moving to next.")
            time.sleep(2)

    print("\n❌ All available live models failed. Please try again later.")
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
