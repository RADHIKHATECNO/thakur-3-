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

# OpenRouter API Key
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    print("❌ ERROR: OPENROUTER_API_KEY is missing in GitHub Secrets!")
    sys.exit(1)

def setup_files():
    if not os.path.exists(CHARACTER_FILE):
        with open(CHARACTER_FILE, "w", encoding="utf-8") as f:
            f.write("CRITICAL: All characters must follow a consistent art style. Describe their age, clothes, face, and accessories in extreme detail.")
    
    if not os.path.exists(STORY_FILE):
        with open(STORY_FILE, "w", encoding="utf-8") as f:
            f.write("4 min | 3D Pixar Animation | Ek lalachi kauwa aur jadui paani ki kahani\n")

def call_openrouter(system_prompt, user_prompt, model_name):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/thakur-3", 
        "X-Title": "YouTube Automation"
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
            return res_json["choices"][0]["message"]["content"]
        else:
            print(f"⚠️ OpenRouter Error with {model_name}: {response.text[:150]}")
            return None
    except Exception as e:
        print(f"⚠️ Request Failed: {e}")
        return None

def get_best_live_free_models():
    """🤖 MAGIC: Live scan for the most powerful FREE models right now!"""
    print("🔍 Scanning OpenRouter for the most powerful LIVE FREE models...")
    try:
        response = requests.get("https://openrouter.ai/api/v1/models", timeout=15)
        if response.status_code == 200:
            models_data = response.json().get("data", [])
            free_models = []
            
            for m in models_data:
                m_id = m.get("id", "")
                pricing = m.get("pricing", {})
                
                # Check if model is free (Prompt & Completion price = 0)
                try: p_prompt = float(pricing.get("prompt", 1))
                except: p_prompt = 1
                try: p_comp = float(pricing.get("completion", 1))
                except: p_comp = 1
                
                # Ignore agentic/coding models that cause errors
                if "thinkingmachines" in m_id.lower() or "lyria" in m_id.lower():
                    continue
                
                if m_id.endswith(":free") or (p_prompt == 0.0 and p_comp == 0.0):
                    ctx_len = m.get("context_length", 0)
                    score = ctx_len
                    
                    # 💡 Rating System: Bonus points for best storytellers
                    lower_id = m_id.lower()
                    if "gemini-2.0" in lower_id: score += 2000000
                    elif "gemini" in lower_id: score += 1000000
                    elif "llama-3.3" in lower_id or "70b" in lower_id: score += 900000
                    elif "qwen" in lower_id and "72b" in lower_id: score += 800000
                    elif "gemma" in lower_id: score += 500000
                    
                    free_models.append({"id": m_id, "score": score})
            
            # Sort by highest score (Most powerful model first)
            free_models.sort(key=lambda x: x["score"], reverse=True)
            top_models = [m["id"] for m in free_models[:10]] 
            
            if top_models:
                print(f"🌟 Found {len(top_models)} active Free Models! Top pick: {top_models[0]}")
                return top_models
    except Exception as e:
        print(f"⚠️ Live scan failed: {e}")
        
    print("⚠️ Using Fallback Free Models.")
    return [
        "google/gemini-2.0-flash-lite-preview-02-05:free",
        "google/gemini-2.0-pro-exp-02-05:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "mistralai/mistral-7b-instruct:free"
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
    - Example: Instead of "a boy", write "a 10-year-old Indian boy with messy curly black hair, large expressive brown eyes, wearing a torn dirty oversized white shirt and blue shorts."
    - COPY-PASTE this exact detailed description every time the character is in the frame.
    
    🚨 SCRIPT RULES:
    1. NEVER NUMBER THE LINES (No 1., 2., 3.). Just write the text.
    2. MICRO-SYNC: 1 Voiceover Line = 1 Highly Detailed Image Prompt.
    
    FORMAT EXACTLY LIKE THIS (Use `|` as separator):
    Ek bhayanak jangal mein ek jadui kauwa rehta tha. | A {style} shot of a sleek black crow with glowing red eyes, sharp beak, wearing a tiny glowing golden locket around its neck, sitting on a dark tree.
    Kauwe ne ek chamakta hua paani ka matka dekha. | A {style} shot of the SAME sleek black crow with glowing red eyes, sharp beak, wearing a tiny glowing golden locket around its neck, looking greedily at a magical glowing earthen pot.
    
    START DIRECTLY WITH THE FIRST LINE. NO INTRO. NO OUTRO."""
    
    models = get_best_live_free_models()
    
    for model in models:
        print(f"🔄 Trying model: {model}...")
        for attempt in range(1, 3): 
            text = call_openrouter(system_prompt, user_prompt, model)
            
            if text:
                valid_lines = []
                for line in text.split('\n'):
                    if '|' in line and not line.startswith('|') and not line.startswith('**'):
                        # Regex se 1. 2. 3. numbers pakke taur par hat jayenge
                        clean_line = re.sub(r'^[\d\.\-\*\s]+', '', line.strip())
                        if len(clean_line) > 10:
                            valid_lines.append(clean_line)
                        
                if len(valid_lines) >= 5:
                    print(f"✅ Success! Generated {len(valid_lines)} micro-scenes using {model}.")
                    return "\n".join(valid_lines)
            time.sleep(2)
            
    print("❌ Failed to generate script. All OpenRouter models failed.")
    sys.exit(1)

def generate_ai_metadata(topic):
    prompt = f"Topic: '{topic}'. Format EXACTLY:\nTITLE: [Clickbaity Viral Title]\nDESC: [Engaging description.]\nTAGS: [tag1, tag2]\nMUSIC: [10-word prompt for AI background music]"
    models = get_best_live_free_models()
    
    for model in models[:5]: # Try top 5 for metadata
        print(f"🎵 Generating Metadata using {model}...")
        text = call_openrouter("You are a YouTube SEO Expert.", prompt, model)
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
    print("🚀 Auto Prompt Stage Completed Successfully!")

if __name__ == "__main__": main()
