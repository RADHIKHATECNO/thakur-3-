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

API_KEY = os.getenv("KIE_API_KEY")
if not API_KEY:
    print("❌ ERROR: KIE_API_KEY is missing in GitHub Secrets!")
    sys.exit(1)

API_URL = "https://api.kie.ai/codex/v1/responses"
MODEL_NAME = "gpt-6-astra"

def setup_files():
    if not os.path.exists(CHARACTER_FILE):
        with open(CHARACTER_FILE, "w", encoding="utf-8") as f:
            f.write("All characters should look realistic and cinematic. Ensure the style is consistent.")
    
    if not os.path.exists(STORY_FILE):
        with open(STORY_FILE, "w", encoding="utf-8") as f:
            f.write("4 min | 3D Pixar Animation | Ek lalachi kauwa aur jadui paani ki kahani\n")
            
def call_kie_api(system_prompt, user_prompt):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    
    data = {
        "model": MODEL_NAME,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": full_prompt
                    }
                ]
            }
        ],
        "reasoning": {
            "effort": "low"
        }
    }
    
    try:
        # Stream=True allows us to read chunk by chunk just like ChatGPT types it
        response = requests.post(API_URL, headers=headers, json=data, stream=True, timeout=120)
        
        if response.status_code != 200:
            print(f"⚠️ KIE API Error ({response.status_code}): {response.text}")
            return None
            
        collected_text = ""
        
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data: "):
                    data_str = decoded[6:].strip()
                    if not data_str or data_str == "[DONE]":
                        continue
                        
                    try:
                        chunk = json.loads(data_str)
                        
                        # Type 1: Final Completed Object
                        if chunk.get("type") == "response.done":
                            outputs = chunk.get("response", {}).get("output", [])
                            for item in outputs:
                                if item.get("type") == "message":
                                    for content in item.get("content", []):
                                        if content.get("type") == "output_text":
                                            return content.get("text")
                        
                        # Type 2: Streaming Deltas (If final object is missing)
                        if chunk.get("type") == "response.text.delta":
                            collected_text += chunk.get("delta", "")
                        elif "delta" in chunk and isinstance(chunk["delta"], dict) and "text" in chunk["delta"]:
                            collected_text += chunk["delta"]["text"]
                            
                    except Exception:
                        pass
        
        if collected_text:
            return collected_text
        else:
            print("⚠️ Stream completed but no text found.")
            return None
            
    except Exception as e:
        print(f"⚠️ Network Request Failed: {e}")
        return None

def generate_ai_script(duration_str, style, topic, character_rules):
    try:
        minutes = int(re.search(r'\d+', duration_str).group())
    except:
        minutes = 1
        
    target_scenes = max(5, math.ceil((minutes * 60) / 3.5))

    system_prompt = "You are an Elite YouTube Scriptwriter and Master Storyboard Artist. You MUST follow instructions strictly."
    
    user_prompt = f"""Task: Write a highly engaging, emotional, and dramatic LONG-FORM YouTube story video.
    Topic: "{topic}"
    Duration Target: Write exactly {target_scenes} short lines of Voiceover.
    
    🚨 THE CHARACTER BIBLE (CRITICAL RULES):
    Here are the design guidelines for this video: "{character_rules}"
    - The OVERALL ART STYLE must be: "{style}".
    
    🚨 SCRIPT RULES:
    1. HOOK: The first 1-2 lines must be extremely suspenseful or shocking.
    2. MICRO-SYNC: Break the story into tiny sentences. 1 Voiceover Line = 1 Detailed Image. Every small action gets its own line.
    
    FORMAT YOUR RESPONSE EXACTLY LIKE THIS (Use `|` as separator):
    [Hindi/Hinglish Voiceover Line] | [Highly Detailed Image Prompt following the Character Bible and Style]
    
    EXAMPLE:
    Ek samay ki baat hai, ek bhayanak jangal mein ek akela aadmi chal raha tha. | A {style} shot of a lone man resembling a young Dev Patel with a red scarf walking through a dark, foggy forest.
    
    START DIRECTLY WITH LINE 1. NO INTRO. NO OUTRO. EXACTLY {target_scenes} LINES."""
    
    max_attempts = 3 
    
    for attempt in range(1, max_attempts + 1):
        print(f"🔄 Attempt {attempt}: Generating Story with KIE API ({MODEL_NAME})...")
        text = call_kie_api(system_prompt, user_prompt)
        
        if text:
            valid_lines = [line.strip() for line in text.split('\n') if '|' in line and not line.startswith('|')]
            if len(valid_lines) >= 5:
                print(f"✅ Success! Generated {len(valid_lines)} micro-scenes/prompts.")
                return "\n".join(valid_lines)
            else:
                print(f"⚠️ AI output format mismatch. Retrying!")
        time.sleep(3)
            
    print("❌ Failed to generate script after 3 attempts.")
    sys.exit(1)

def generate_ai_metadata(topic):
    prompt = f"""Topic: '{topic}'.
    Create highly VIRAL YouTube Long-form Video metadata.
    Format EXACTLY:
    TITLE: [Clickbaity Viral Title in Hindi/English (Max 70 chars)]
    DESC: [Engaging description. Tease the story.]
    TAGS: [comma separated top 10 SEO tags]
    MUSIC: [10-word prompt for AI background music, e.g., 'epic sad cinematic emotional']"""
    
    print(f"🎵 Generating Metadata using {MODEL_NAME}...")
    text = call_kie_api("You are a YouTube SEO Expert.", prompt)
    
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
        duration_str, style, topic = "2 min", "Cinematic Realistic", stories[0]
        
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
