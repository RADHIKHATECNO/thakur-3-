import os
import sys
import math
import re
import time
import json
import urllib.request
from openai import OpenAI

STORY_FILE = "story.txt"
PROMPT_FILE = "prompts.txt"
METADATA_FILE = "metadata.txt"

API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    sys.exit(1)
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

def get_live_free_models():
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
        free_models = [m["id"] for m in data.get("data", []) if m.get("pricing", {}).get("prompt") == "0" and m.get("pricing", {}).get("completion") == "0"]
        return free_models[:5] if free_models else ["google/gemini-2.0-flash-lite-preview-02-05:free"]
    except:
        return ["google/gemini-2.0-flash-lite-preview-02-05:free", "meta-llama/llama-3.2-3b-instruct:free"]

def smart_ai_request(system_prompt, user_prompt, description):
    free_models = get_live_free_models()
    for model_name in free_models:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.8
            )
            text = response.choices[0].message.content
            if text: return text
        except:
            time.sleep(2)
    return None

def generate_ai_script(duration_sec, topic):
    target_scenes = max(2, math.ceil(int(duration_sec) / 5))
    system_prompt = "You are a highly aggressive Action-Drama Director. Output ONLY the requested format. NO tables. NO markdown."
    user_prompt = f"""Task: Create a FAST-PACED, emotional action story based on: "{topic}". Exactly {target_scenes} scenes.

    🚨 HIGH-RETENTION VISUALS:
    - Constant Motion (Running, dodging, panicking). NO static scenes.
    - Safe for Monetization. Use 'storm', 'shadows', 'ruins'.

    🚨 AUDIO RULES:
    - NO BGM. NO VOICE.
    - ONLY HIGH-VOLUME FOLEY SOUND EFFECTS (e.g., "Loud water splashing, heavy rapid panting").
    - End every Video Prompt with exactly: "NO BGM, NO VOICE."

    FORMAT RULES: [Image Prompt] | [Video Prompt]
    1. Invent a specific character and copy-paste it at the beginning of EVERY Image prompt.
    2. One '|' per line. NO TABLES.
    """
    text = smart_ai_request(system_prompt, user_prompt, "Generating Script")
    if text:
        valid_lines = [line.strip() for line in text.split('\n') if '|' in line and not line.strip().startswith('|') and '---' not in line]
        if valid_lines: return "\n".join(valid_lines[:target_scenes])
    return None

def generate_ai_metadata(topic):
    system_prompt = "You are a highly creative Music Director and YouTube SEO Expert."
    
    user_prompt = f"""Story Topic: '{topic}'.
    Create Advertiser-Friendly YouTube Shorts metadata and a Custom Music Prompt.
    
    1. TITLE: Exactly 40 to 60 characters long.
    2. DESC: Exactly 200 to 300 characters long.
    3. TAGS: Exactly 5 to 6 comma-separated tags.
    4. MUSIC: Read the Story Topic carefully. Write a 100% UNIQUE 5-8 word background music prompt matching the EXACT emotion of this specific story. 
    DO NOT repeat old prompts. DO NOT be generic. 
    (Example logic: If it's a flood -> "dark heavy rainy intense bass", If chasing -> "fast panic heartbeat aggressive drums", If sad dog -> "crying emotional slow lonely acoustic guitar").
    
    Format EXACTLY like this:
    TITLE: [Title]
    DESC: [Description]
    TAGS: [tag1, tag2, tag3]
    MUSIC: [Your 100% Unique Music Prompt Here]"""
    
    text = smart_ai_request(system_prompt, user_prompt, "Generating Metadata")
    music_prompt = "dark emotional cinematic background score" 
    
    if text:
        try:
            title = re.search(r"TITLE:\s*(.*)", text).group(1).strip()
            desc = re.search(r"DESC:\s*([\s\S]*?)TAGS:", text).group(1).strip()
            tags = re.search(r"TAGS:\s*(.*)", text).group(1).strip()
            music_prompt = re.search(r"MUSIC:\s*(.*)", text).group(1).strip()
            
            with open("music_prompt.txt", "w", encoding="utf-8") as f:
                f.write(music_prompt)
            return title, desc, tags
        except: pass
        
    with open("music_prompt.txt", "w", encoding="utf-8") as f:
        f.write(music_prompt)
    return "Heart Touching Emotional Story 😭", "A very sad emotional story about life.", "shorts, sad, story, emotional, viral"

def process_stories():
    if not os.path.exists(STORY_FILE): sys.exit(1)
    with open(STORY_FILE, "r", encoding="utf-8") as f: content = f.read().strip()
    if not content: sys.exit(1)
    topics = [t.strip() for t in content.split("\n") if t.strip()]
    parts = topics[0].split("|")
    duration_sec, topic = (int(re.search(r'\d+', parts[0]).group()), parts[1].strip()) if len(parts) > 1 else (30, topics[0])
    
    ai_output = generate_ai_script(duration_sec, topic)
    if not ai_output: sys.exit(1)
    with open(PROMPT_FILE, "w", encoding="utf-8") as f: f.write(ai_output + "\n")
    
    title, desc, tags = generate_ai_metadata(topic)
    with open(METADATA_FILE, "w", encoding="utf-8") as f: f.write(f"TITLE: {title}\nDESC: {desc}\nTAGS: {tags}")
    with open(STORY_FILE, "w", encoding="utf-8") as f: f.write("\n".join(topics[1:]) + "\n" if len(topics) > 1 else "")

if __name__ == "__main__":
    process_stories()
