import os
import sys
import re
import math
import time
import urllib.request
import json
from openai import OpenAI

STORY_FILE = "story.txt"
CHARACTER_FILE = "character.txt"
PROMPT_FILE = "prompts.txt"
METADATA_FILE = "metadata.txt"

API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    print("❌ ERROR: OPENROUTER_API_KEY is missing!")
    sys.exit(1)

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

def get_live_free_models():
    """Bhai ka Original Logic: Jo live check karega ki konsa model abhi FREE hai"""
    models_list = []
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
        # Live free models filter
        models_list = [
            m["id"] for m in data.get("data", []) 
            if m.get("pricing", {}).get("prompt") == "0" 
            and m.get("pricing", {}).get("completion") == "0"
        ]
        print(f"🌐 Found {len(models_list)} Live Free Models from OpenRouter API.")
    except Exception as e:
        print(f"⚠️ Failed to fetch live models from API: {e}")
        
    # Guaranteed Fallbacks (Agar API fail ho jaye)
    fallbacks = [
        "google/gemini-2.0-flash-exp:free",
        "google/gemini-2.0-pro-exp-02-05:free",
        "sophosympatheia/rogue-rose-103b-v0.2:free",
        "qwen/qwen-vl-plus:free",
        "mistralai/mistral-7b-instruct:free"
    ]
    
    for fb in fallbacks:
        if fb not in models_list:
            models_list.append(fb)
            
    return models_list

def setup_files():
    if not os.path.exists(CHARACTER_FILE):
        with open(CHARACTER_FILE, "w", encoding="utf-8") as f:
            f.write("All characters should look realistic and cinematic. Wear ancient Indian style clothes. Ensure the style is consistent.")
    
    if not os.path.exists(STORY_FILE):
        with open(STORY_FILE, "w", encoding="utf-8") as f:
            f.write("3 min | 3D Pixar Animation | Ek lalachii kauwa aur jadui paani\n")
            
def generate_ai_script(duration_str, style, topic, character_rules):
    try:
        minutes = int(re.search(r'\d+', duration_str).group())
    except:
        minutes = 1
    # Assuming 1 scene every 3.5 seconds
    target_scenes = max(5, math.ceil((minutes * 60) / 3.5))

    system_prompt = "You are an Elite YouTube Scriptwriter and Master Storyboard Artist. You MUST follow instructions strictly."
    
    user_prompt = f"""Task: Write a highly engaging, emotional, and dramatic LONG-FORM YouTube story video.
    Topic: "{topic}"
    Duration Target: Write exactly {target_scenes} short lines of Voiceover.
    
    🚨 THE CHARACTER BIBLE (CRITICAL RULES):
    Here are the design guidelines for this video: "{character_rules}"
    - The OVERALL ART STYLE must be: "{style}".
    - Do NOT make all characters look the same (no clones/twins). 
    - Keep character outfits and features consistent throughout the story. If a King has a golden crown in scene 1, he must have it in scene 20.
    
    🚨 SCRIPT RULES:
    1. HOOK: The first 1-2 lines must be extremely suspenseful or shocking.
    2. MICRO-SYNC: Break the story into tiny sentences. 1 Voiceover Line = 1 Detailed Image. Every small action gets its own line.
    
    FORMAT YOUR RESPONSE EXACTLY LIKE THIS (Use `|` as separator):
    [Hindi/Hinglish Voiceover Line] | [Highly Detailed Image Prompt following the Character Bible and Style]
    
    EXAMPLE:
    Ek samay ki baat hai, ek bhayanak jangal mein ek akela aadmi chal raha tha. | A wide shot of a lone man with a red scarf walking through a dark, foggy, terrifying forest. {style}.
    
    START DIRECTLY WITH LINE 1. NO INTRO. NO OUTRO. EXACTLY {target_scenes} LINES."""
    
    models = get_live_free_models()
    max_attempts = 15 # Will try up to 15 different models/attempts
    attempt = 1
    
    for model_name in models:
        for _ in range(2): # Try each model 2 times
            if attempt > max_attempts:
                print("❌ ERROR: Tried too many times. All AI models failed.")
                sys.exit(1)
                
            try:
                print(f"🔄 Attempt {attempt}: Generating Story with {model_name}...")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    temperature=0.8
                )
                text = response.choices[0].message.content
                
                valid_lines = [line.strip() for line in text.split('\n') if '|' in line and not line.startswith('|')]
                if len(valid_lines) >= 5:
                    print(f"✅ Success! Generated {len(valid_lines)} micro-scenes/prompts from {model_name}.")
                    return "\n".join(valid_lines)
                else:
                    print(f"⚠️ Model {model_name} gave bad format. Retrying...")
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️ {model_name} failed: {error_msg[:100]}...")
                time.sleep(2)
                
            attempt += 1
            
    print("❌ Failed to generate script after all attempts.")
    sys.exit(1)

def generate_ai_metadata(topic):
    prompt = f"""Topic: '{topic}'.
    Create highly VIRAL, HIGH-SEARCH-VOLUME YouTube Long-form Video metadata.
    Format EXACTLY:
    TITLE: [Clickbaity Viral Title in English/Hindi (Max 70 chars)]
    DESC: [A highly engaging description. Tease the story but don't reveal the ending.]
    TAGS: [comma separated top 10 SEO tags]
    MUSIC: [10-word prompt for AI background music, e.g., 'epic sad cinematic emotional']"""
    
    models = get_live_free_models()
    for model_name in models[:5]: # Try first 5 models for metadata
        try:
            print(f"🎵 Generating Metadata using {model_name}...")
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": "You are a YouTube SEO Expert."}, {"role": "user", "content": prompt}],
                temperature=0.8
            )
            text = response.choices[0].message.content
            
            title = re.search(r"TITLE:\s*(.*)", text).group(1).strip()
            desc = re.search(r"DESC:\s*([\s\S]*?)TAGS:", text).group(1).strip()
            tags = re.search(r"TAGS:\s*(.*)", text).group(1).strip()
            music = re.search(r"MUSIC:\s*(.*)", text).group(1).strip()
            
            with open("music_prompt.txt", "w", encoding="utf-8") as f: f.write(music)
            return title, desc, tags
        except:
            time.sleep(1)
            
    with open("music_prompt.txt", "w", encoding="utf-8") as f: f.write("epic emotional cinematic storytelling background score")
    return "Amazing Story You Must Watch 🔥", "Watch this amazing story till the end!", "story, viral, trending"

def main():
    setup_files()
    
    with open(STORY_FILE, "r", encoding="utf-8") as f: 
        stories = [line.strip() for line in f.readlines() if line.strip()]
        
    with open(CHARACTER_FILE, "r", encoding="utf-8") as f:
        character_rules = f.read().strip()
        
    if not stories:
        print("❌ No topics found in story.txt!")
        sys.exit(1)
        
    parts = [p.strip() for p in stories[0].split("|")]
    if len(parts) >= 3:
        duration_str, style, topic = parts[0], parts[1], parts[2]
    else:
        duration_str, style, topic = "3 min", "Cinematic Realistic", stories[0]
        
    print(f"🎬 Planning: {topic} | Length: {duration_str} | Style: {style}")
    
    script_content = generate_ai_script(duration_str, style, topic, character_rules)
    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        f.write(script_content + "\n")
        
    title, desc, tags = generate_ai_metadata(topic)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        f.write(f"TITLE: {title}\nDESC: {desc}\nTAGS: {tags}")
        
    with open(STORY_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(stories[1:]) + "\n" if len(stories) > 1 else "")
        
    print("🚀 Auto Prompt Stage Completed Successfully!")

if __name__ == "__main__":
    main()
