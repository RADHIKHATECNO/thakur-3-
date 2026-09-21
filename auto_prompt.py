import os
import sys
import re
import math
import time
import requests
import json

STORY_FILE = "story.txt"
CHARACTER_FILE = "character.txt"
PROMPT_FILE = "prompts.txt"
METADATA_FILE = "metadata.txt"
MUSIC_PROMPT_FILE = "music_prompt.txt"

API_KEY = os.getenv("BAZAAR_API_KEY")

def call_bazaar_api(system_prompt, user_prompt, model_name):
    if not API_KEY:
        print("❌ BAZAAR_API_KEY is missing!")
        sys.exit(1)
        
    url = "https://api.bazaarlink.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": model_name,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=90)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"⚠️ Error with {model_name}: {e}")
    return None

def generate_script(duration_str, style, topic, character_rules):
    try:
        minutes = float(re.search(r'[\d\.]+', duration_str).group())
    except:
        minutes = 1.0
        
    # 1 line takes roughly 4 seconds. Calculate exact number of micro-scenes.
    target_scenes = max(5, math.ceil((minutes * 60) / 4.0))
    
    system = "You are a master YouTube Storyteller. Write engaging Hindi/Hinglish stories and DETAILED image prompts."
    user = f"""Task: Write a highly engaging YouTube story video.
Topic: "{topic}"
Length: EXACTLY {target_scenes} short lines of Voiceover.
Style: "{style}"
Rules for Characters: "{character_rules}"

STRICT RULES:
1. First line MUST be a 10-second HOOK (suspense/shocking).
2. Write in short sentences (Max 10-15 words per line).
3. Format MUST be exactly: Voiceover Line | Detailed Image Prompt
4. DO NOT number the lines. DO NOT add Intros or Outros.

Example:
Ek gaon mein ek jadui ped tha. | A {style} shot of a magical glowing tree in an Indian village.
Jab us ped par paani dala, toh sone ke sikke gire! | A {style} shot of gold coins falling from the magical tree's branches."""

    models = ["auto:free", "google/gemini-2.5-flash", "deepseek/deepseek-v4-flash-0731free"]
    
    for model in models:
        print(f"🔄 Generating script with {model}...")
        text = call_bazaar_api(system, user, model)
        if text:
            lines = [l.strip() for l in text.split('\n') if '|' in l and len(l) > 10]
            if len(lines) >= 5:
                print(f"✅ Generated {len(lines)} perfect micro-scenes!")
                return "\n".join(lines)
    print("❌ Failed to generate script.")
    sys.exit(1)

def generate_metadata(topic):
    system = "You are a YouTube SEO Expert."
    prompt = f"Topic: '{topic}'. Generate viral metadata.\nFormat EXACTLY:\nTITLE: [Clickbaity Viral Title]\nDESC: [Description]\nTAGS: [tag1, tag2]\nMUSIC: [10-word prompt for AI background music]"
    
    text = call_bazaar_api(system, prompt, "auto:free")
    if text:
        try:
            title = re.search(r"TITLE:\s*(.*)", text).group(1).strip().replace('*', '')
            desc = re.search(r"DESC:\s*([\s\S]*?)TAGS:", text).group(1).strip()
            tags = re.search(r"TAGS:\s*(.*)", text).group(1).strip().replace('*', '')
            music = re.search(r"MUSIC:\s*(.*)", text).group(1).strip().replace('*', '')
            
            with open(MUSIC_PROMPT_FILE, "w", encoding="utf-8") as f: f.write(music)
            return title, desc, tags
        except: pass
    
    with open(MUSIC_PROMPT_FILE, "w", encoding="utf-8") as f: f.write("epic cinematic cinematic background score")
    return "Amazing Viral Story 🔥", "Watch till the end!", "story, viral, trending"

def main():
    if not os.path.exists(CHARACTER_FILE):
        with open(CHARACTER_FILE, "w", encoding="utf-8") as f: f.write("Make characters look consistent.")
    if not os.path.exists(STORY_FILE):
        with open(STORY_FILE, "w", encoding="utf-8") as f: f.write("1 min | 3D Pixar | Lalachi kauwa")
        
    with open(STORY_FILE, "r", encoding="utf-8") as f:
        stories = [line.strip() for line in f.readlines() if line.strip()]
        
    if not stories: sys.exit(1)
    
    parts = stories[0].split("|")
    duration, style, topic = parts[0].strip(), parts[1].strip(), parts[2].strip() if len(parts) >= 3 else stories[0]
    
    with open(CHARACTER_FILE, "r", encoding="utf-8") as f:
        char_rules = f.read().strip()
        
    script = generate_script(duration, style, topic, char_rules)
    title, desc, tags = generate_metadata(topic)
    
    with open(PROMPT_FILE, "w", encoding="utf-8") as f: f.write(script + "\n")
    with open(METADATA_FILE, "w", encoding="utf-8") as f: f.write(f"TITLE: {title}\nDESC: {desc}\nTAGS: {tags}")
    
    with open(STORY_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(stories[1:]) + "\n" if len(stories) > 1 else "")
    print("🚀 Script & SEO ready!")

if __name__ == "__main__":
    main()
