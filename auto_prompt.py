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

# BazaarLink API Key from GitHub Secrets
API_KEY = os.getenv("BAZAAR_API_KEY")
if not API_KEY:
    print("❌ ERROR: BAZAAR_API_KEY is missing in GitHub Secrets!")
    sys.exit(1)

def setup_files():
    if not os.path.exists(CHARACTER_FILE):
        with open(CHARACTER_FILE, "w", encoding="utf-8") as f:
            f.write("CRITICAL: All characters must follow a consistent art style. Describe their age, clothes, face, and accessories in extreme detail.")
    
    if not os.path.exists(STORY_FILE):
        with open(STORY_FILE, "w", encoding="utf-8") as f:
            f.write("4 min | 3D Pixar Animation | Ek lalachi kauwa aur jadui paani ki kahani\n")

def call_bazaar_api_stream(system_prompt, user_prompt, model_name):
    """🤖 MAGIC: BazaarLink API with LIVE Typing and Auto-Free Routing!"""
    
    # BazaarLink Official OpenAI-compatible endpoint
    url = "https://api.bazaarlink.ai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "stream": True # 🔴 Live Typing On!
    }
    
    print("\n✍️ AI is typing LIVE:\n--------------------------------------------------")
    full_text = ""
    
    try:
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=90)
        
        if response.status_code != 200:
            print(f"\n⚠️ BazaarLink Error with {model_name}: {response.text[:150]}")
            return None
            
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    json_str = decoded_line[6:]
                    if json_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(json_str)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            full_text += content
                            sys.stdout.write(content)
                            sys.stdout.flush()
                    except:
                        pass
                        
        print("\n--------------------------------------------------\n✅ AI Finished Typing!")
        return full_text
        
    except Exception as e:
        print(f"\n⚠️ Request Failed for {model_name}: {e}")
        return None

def get_best_bazaar_models():
    """
    BazaarLink Docs Magic: 'auto:free' automatically finds the best 
    available free models (DeepSeek, Qwen) and routes to them instantly!
    """
    return [
        "auto:free",                           # 🌟 No. 1 Priority: Let BazaarLink automatically pick the best live free model
        "deepseek/deepseek-v4-flash-0731free", # Fallback Free Model 1 (from docs)
        "qwen/qwen3.7-flash",                  # Fallback Free Model 2 (from docs)
        "google/gemini-2.5-flash"              # Universal Fallback
    ]

def generate_ai_script(duration_str, style, topic, character_rules):
    try:
        minutes = int(re.search(r'\d+', duration_str).group())
    except:
        minutes = 1
        
    target_scenes = max(5, math.ceil((minutes * 60) / 3.5))

    system_prompt = "You are a master Bollywood Storyteller and a DALL-E 3 Prompt Expert. You write highly emotional Hindi/Hinglish stories and EXTREMELY DETAILED image prompts. OUTPUT ONLY THE STORY LINES. DO NOT NUMBER THE LINES."
    
    user_prompt = f"""Task: Write a highly engaging LONG-FORM YouTube story video.
    Topic: "{topic}"
    Duration Target: EXACTLY {target_scenes} short lines of Voiceover.
    
    🚨 CHARACTER BIBLE & EXTREME DETAILING (DO OR DIE):
    Bing/DALL-E forgets characters between scenes. You MUST write HIGHLY DETAILED physical descriptions for EVERY character in EVERY prompt they appear in.
    Character Rules: "{character_rules}"
    Art Style: "{style}"
    
    - Describe their face, age, body type, exact clothing, colors, and accessories in EVERY single scene.
    - COPY-PASTE this exact detailed description every time the character is in the frame.
    
    🚨 SCRIPT RULES:
    1. NEVER NUMBER THE LINES (No 1., 2., 3.). Just write the text.
    2. MICRO-SYNC: 1 Voiceover Line = 1 Highly Detailed Image Prompt.
    
    FORMAT EXACTLY LIKE THIS (Use `|` as separator):
    Ek bhayanak jangal mein ek jadui kauwa rehta tha. | A {style} shot of a sleek black crow with glowing red eyes, sharp beak, wearing a tiny glowing golden locket around its neck, sitting on a dark tree.
    Kauwe ne ek chamakta hua paani ka matka dekha. | A {style} shot of the SAME sleek black crow with glowing red eyes, sharp beak, wearing a tiny glowing golden locket around its neck, looking greedily at a magical glowing earthen pot.
    
    START DIRECTLY WITH THE FIRST LINE. NO INTRO. NO OUTRO."""
    
    models = get_best_bazaar_models()
    
    for model in models:
        print(f"\n🔄 Trying model: {model}...")
        for attempt in range(1, 3): 
            text = call_bazaar_api_stream(system_prompt, user_prompt, model)
            
            if text:
                valid_lines = []
                for line in text.split('\n'):
                    if '|' in line and not line.startswith('|') and not line.startswith('**'):
                        clean_line = re.sub(r'^[\d\.\-\*\s]+', '', line.strip())
                        if len(clean_line) > 10:
                            valid_lines.append(clean_line)
                        
                if len(valid_lines) >= 5:
                    print(f"✅ Success! Extracted {len(valid_lines)} micro-scenes from the LIVE output.")
                    return "\n".join(valid_lines)
            time.sleep(2)
            
    print("❌ Failed to generate script. All BazaarLink models failed.")
    sys.exit(1)

def generate_ai_metadata(topic):
    prompt = f"Topic: '{topic}'. Format EXACTLY:\nTITLE: [Clickbaity Viral Title]\nDESC: [Engaging description.]\nTAGS: [tag1, tag2]\nMUSIC: [10-word prompt for AI background music]"
    models = get_best_bazaar_models()
    
    for model in models[:3]:
        print(f"\n🎵 Generating Metadata using {model}...")
        text = call_bazaar_api_stream("You are a YouTube SEO Expert.", prompt, model)
        if text:
            try:
                title = re.search(r"TITLE:\s*(.*)", text).group(1).strip()
                desc = re.search(r"DESC:\s*([\s\S]*?)TAGS:", text).group(1).strip()
                tags = re.search(r"TAGS:\s*(.*)", text).group(1).strip()
                music = re.search(r"MUSIC:\s*(.*)", text).group(1).strip()
                
                title = title.replace('*', '')
                tags = tags.replace('*', '')
                music = music.replace('*', '')
                
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
        
    print(f"🎬 Planning: {topic} | Length: {duration_str} | Style: {style}")
    
    script_content = generate_ai_script(duration_str, style, topic, character_rules)
    with open(PROMPT_FILE, "w", encoding="utf-8") as f: f.write(script_content + "\n")
        
    title, desc, tags = generate_ai_metadata(topic)
    with open(METADATA_FILE, "w", encoding="utf-8") as f: f.write(f"TITLE: {title}\nDESC: {desc}\nTAGS: {tags}")
    with open(STORY_FILE, "w", encoding="utf-8") as f: f.write("\n".join(stories[1:]) + "\n" if len(stories) > 1 else "")
    print("\n🚀 Auto Prompt Stage Completed Successfully!")

if __name__ == "__main__": main()
