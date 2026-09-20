import os
import sys
import re
import math
import time
import requests

STORY_FILE = "story.txt"
CHARACTER_FILE = "character.txt"
PROMPT_FILE = "prompts.txt"
METADATA_FILE = "metadata.txt"

API_KEY = os.getenv("COHERE_API_KEY")
if not API_KEY:
    print("❌ ERROR: COHERE_API_KEY is missing in GitHub Secrets!")
    sys.exit(1)

def setup_files():
    if not os.path.exists(CHARACTER_FILE):
        with open(CHARACTER_FILE, "w", encoding="utf-8") as f:
            f.write("All characters should look realistic and cinematic. Ensure the style is consistent.")
    
    if not os.path.exists(STORY_FILE):
        with open(STORY_FILE, "w", encoding="utf-8") as f:
            f.write("4 min | 3D Pixar Animation | Ek lalachi kauwa aur jadui paani ki kahani\n")
            
def call_cohere_api_v2(system_prompt, user_prompt, model_name):
    url = "https://api.cohere.com/v2/chat"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    data = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=90)
        if response.status_code == 200:
            res_json = response.json()
            try:
                contents = res_json["message"]["content"]
                for item in contents:
                    if item.get("type") == "text":
                        return item.get("text")
                return None
            except KeyError:
                return None
        else:
            return None
    except Exception as e:
        return None

def generate_ai_script(duration_str, style, topic, character_rules):
    try:
        minutes = int(re.search(r'\d+', duration_str).group())
    except:
        minutes = 1
        
    target_scenes = max(5, math.ceil((minutes * 60) / 3.5))

    system_prompt = "You are an Elite YouTube Scriptwriter and Master Storyboard Artist. Output ONLY the story lines. DO NOT add numbers like 1., 2., 3. before the lines."
    
    user_prompt = f"""Task: Write a highly engaging, emotional, and dramatic LONG-FORM YouTube story video.
    Topic: "{topic}"
    Duration Target: Write exactly {target_scenes} short lines of Voiceover.
    
    🚨 THE CHARACTER BIBLE (CRITICAL RULES):
    "{character_rules}"
    - The OVERALL ART STYLE must be: "{style}".
    
    🚨 SCRIPT RULES:
    1. DO NOT NUMBER THE LINES. Start directly with the story text.
    2. MICRO-SYNC: Break the story into tiny sentences. 1 Voiceover Line = 1 Detailed Image.
    
    FORMAT YOUR RESPONSE EXACTLY LIKE THIS (Use `|` as separator):
    Ek samay ki baat hai, ek bhayanak jangal mein ek akela aadmi chal raha tha. | A {style} shot of a lone man resembling a young Dev Patel with a red scarf walking through a dark, foggy forest.
    Achanak usne ek ajeeb aawaz suni. | A {style} close-up shot of the same man looking terrified.
    
    START DIRECTLY WITH THE FIRST LINE. NO INTRO. NO NUMBERS."""
    
    active_models = ["command-a-03-2025", "command-a-plus-05-2026", "c4ai-aya-expanse-32b"]
    
    for model in active_models:
        print(f"🔄 Trying model: {model} (V2 API)...")
        for attempt in range(1, 3): 
            text = call_cohere_api_v2(system_prompt, user_prompt, model)
            
            if text:
                valid_lines = []
                for line in text.split('\n'):
                    if '|' in line and not line.startswith('|'):
                        # 🔴 MAGIC FIX: Ye line script se 1. 2. 3. hamesha ke liye hata degi
                        clean_line = re.sub(r'^[\d\.\-\*\s]+', '', line.strip())
                        valid_lines.append(clean_line)
                        
                if len(valid_lines) >= 5:
                    print(f"✅ Success! Generated {len(valid_lines)} micro-scenes/prompts using {model}.")
                    return "\n".join(valid_lines)
            time.sleep(2)
            
    print("❌ Failed to generate script. All models failed.")
    sys.exit(1)

def generate_ai_metadata(topic):
    prompt = f"Topic: '{topic}'. Format EXACTLY:\nTITLE: [Clickbaity Viral Title]\nDESC: [Engaging description.]\nTAGS: [tag1, tag2]\nMUSIC: [10-word prompt for AI background music]"
    active_models = ["command-a-03-2025", "command-a-plus-05-2026", "c4ai-aya-expanse-32b"]
    for model in active_models:
        text = call_cohere_api_v2("You are a YouTube SEO Expert.", prompt, model)
        if text:
            try:
                title = re.search(r"TITLE:\s*(.*)", text).group(1).strip()
                desc = re.search(r"DESC:\s*([\s\S]*?)TAGS:", text).group(1).strip()
                tags = re.search(r"TAGS:\s*(.*)", text).group(1).strip()
                music = re.search(r"MUSIC:\s*(.*)", text).group(1).strip()
                with open("music_prompt.txt", "w", encoding="utf-8") as f: f.write(music)
                return title, desc, tags
            except Exception:
                pass
    with open("music_prompt.txt", "w", encoding="utf-8") as f: f.write("epic emotional cinematic storytelling background score")
    return "Amazing Story You Must Watch 🔥", "Watch this amazing story till the end!", "story, viral, trending"

def main():
    setup_files()
    with open(STORY_FILE, "r", encoding="utf-8") as f: stories = [line.strip() for line in f.readlines() if line.strip()]
    with open(CHARACTER_FILE, "r", encoding="utf-8") as f: character_rules = f.read().strip()
    if not stories: sys.exit(1)
        
    parts = [p.strip() for p in stories[0].split("|")]
    if len(parts) >= 3: duration_str, style, topic = parts[0], parts[1], parts[2]
    else: duration_str, style, topic = "2 min", "Cinematic Realistic", stories[0]
        
    script_content = generate_ai_script(duration_str, style, topic, character_rules)
    with open(PROMPT_FILE, "w", encoding="utf-8") as f: f.write(script_content + "\n")
        
    title, desc, tags = generate_ai_metadata(topic)
    with open(METADATA_FILE, "w", encoding="utf-8") as f: f.write(f"TITLE: {title}\nDESC: {desc}\nTAGS: {tags}")
    with open(STORY_FILE, "w", encoding="utf-8") as f: f.write("\n".join(stories[1:]) + "\n" if len(stories) > 1 else "")
    print("🚀 Auto Prompt Stage Completed Successfully!")

if __name__ == "__main__": main()
