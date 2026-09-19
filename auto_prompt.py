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
DIALOGUE_FILE = "dialogue.txt"

API_KEY = os.getenv("OPENROUTER_API_KEY")
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

def get_live_free_models():
    fallbacks = [
        "google/gemini-2.0-flash-lite-preview-02-05:free", 
        "meta-llama/llama-3.3-70b-instruct:free",
        "cognitivecomputations/dolphin3.0-r1-mistral-24b:free"
    ]
    return fallbacks

def generate_ai_script(duration_sec, topic):
    target_scenes = max(3, math.ceil(int(duration_sec) / 5)) 
    system_prompt = "You are a Master Visual Storyteller. Follow instructions STRICTLY. NO intros. ONLY output the requested format."
    
    user_prompt = f"""Task: Create a highly viral, engaging YouTube Short visual script about: "{topic}".
    Total Scenes: EXACTLY {target_scenes}.

    🚨 VIRAL RULES:
    1. 5-SECOND HOOK: Scene 1 must be visually shocking to stop scrolling.
    2. THE PERFECT LOOP: The EXACT visual description of Scene 1 MUST be repeated perfectly as the LAST SCENE. This creates a seamless loop!
    3. DIALOGUE: Scene 1 needs a short, suspenseful Voiceover Dialogue (in Hinglish or English). All other scenes must have "NONE" for dialogue.
    4. STRICT FORMAT: Do NOT use numbers, bullet points, or intros. Use ONLY the `|` symbol.

    FORMAT EACH LINE EXACTLY LIKE THIS:
    A boy looking terrified at the sky | fast zoom in | Wait, you won't believe what happened next...
    A massive spaceship appearing | slow motion pan | NONE
    A boy looking terrified at the sky | fast zoom in | NONE

    START DIRECTLY WITH SCENE 1:"""
    
    models = get_live_free_models()
    for model_name in models:
        print(f"🔄 Trying model: {model_name}...")
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    temperature=0.7
                )
                text = response.choices[0].message.content
                print(f"\n--- RAW AI OUTPUT ({model_name}) ---\n{text}\n-----------------------")
                
                valid_lines = []
                for line in text.split('\n'):
                    line = line.strip()
                    # 🔴 FIX: Galti se aaye numbers (1., 2.) aur bullet points ko hata dega
                    line = re.sub(r'^[\d\.\-\*\s]+', '', line) 
                    
                    if '|' in line and not line.startswith('---') and not line.lower().startswith('visual'):
                        valid_lines.append(line)
                
                if len(valid_lines) >= 2:
                    parts = valid_lines[0].split('|')
                    if len(parts) >= 3:
                        dialogue = parts[2].strip()
                        if dialogue.upper() != "NONE":
                            with open(DIALOGUE_FILE, "w", encoding="utf-8") as f:
                                f.write(dialogue)
                    return "\n".join(valid_lines[:target_scenes])
                else:
                    print(f"⚠️ Warning: Model didn't return proper `|` format.")
            except Exception as e:
                print(f"⚠️ Error with model {model_name}: {e}")
                time.sleep(2)
    return None

def generate_ai_metadata(topic):
    system_prompt = "You are a Gen-Z viral YouTube SEO Expert."
    user_prompt = f"""Story Topic: '{topic}'.
    Create highly viral, clickbaity YouTube Shorts metadata. No robotic language. Use emojis.
    Title should be curious like "Wait for the end 🤯" or "Bro really did that 💀".
    
    Format EXACTLY like this:
    TITLE: [Viral Title]
    DESC: [Short engaging description asking a question to get comments]
    TAGS: [shorts, viral, trending, fyp, + 3 topic tags]
    MUSIC: [Unique 5-8 word music prompt like 'dark sigma phonk drift']"""
    
    models = get_live_free_models()
    music_prompt = "dark emotional cinematic background score" 
    
    for model_name in models:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.8
            )
            text = response.choices[0].message.content
            title = re.search(r"TITLE:\s*(.*)", text).group(1).strip()
            desc = re.search(r"DESC:\s*([\s\S]*?)TAGS:", text).group(1).strip()
            tags = re.search(r"TAGS:\s*(.*)", text).group(1).strip()
            music_prompt = re.search(r"MUSIC:\s*(.*)", text).group(1).strip()
            
            with open("music_prompt.txt", "w", encoding="utf-8") as f: f.write(music_prompt)
            return title, desc, tags
        except:
            pass
            
    with open("music_prompt.txt", "w", encoding="utf-8") as f: f.write(music_prompt)
    return "Wait for the end 🤯", "What would you do in this situation? Let me know in the comments!", "shorts, viral, trending"

def process_stories():
    if not os.path.exists(STORY_FILE): sys.exit(1)
    with open(STORY_FILE, "r", encoding="utf-8") as f: content = f.read().strip()
    if not content: sys.exit(1)
        
    topics = [t.strip() for t in content.split("\n") if t.strip()]
    parts = topics[0].split("|")
    duration_sec, topic = (int(re.search(r'\d+', parts[0]).group()), parts[1].strip()) if len(parts) > 1 else (30, topics[0])
    
    ai_output = generate_ai_script(duration_sec, topic)
    
    # 🔴 BULLETPROOF FAIL-SAFE: Agar AI puri tarah fail ho jaye to crash nahi hoga!
    if not ai_output:
        print("❌ CRITICAL: AI failed to generate script. Using Fallback Backup Script!")
        fallback_dialogue = "Aapko yakeen nahi hoga isne kya kiya..."
        ai_output = f"""A cinematic and dramatic shot related to {topic} | slow cinematic pan | {fallback_dialogue}
Action happening in the middle related to {topic} | fast motion | NONE
A cinematic and dramatic shot related to {topic} | slow cinematic pan | NONE"""
        
        with open(DIALOGUE_FILE, "w", encoding="utf-8") as f: 
            f.write(fallback_dialogue)
            
    with open(PROMPT_FILE, "w", encoding="utf-8") as f: 
        f.write(ai_output + "\n")
    
    title, desc, tags = generate_ai_metadata(topic)
    with open(METADATA_FILE, "w", encoding="utf-8") as f: f.write(f"TITLE: {title}\nDESC: {desc}\nTAGS: {tags}")
    
    with open(STORY_FILE, "w", encoding="utf-8") as f: 
        f.write("\n".join(topics[1:]) + "\n" if len(topics) > 1 else "")

if __name__ == "__main__":
    process_stories()
