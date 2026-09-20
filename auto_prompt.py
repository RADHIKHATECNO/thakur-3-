import os
import sys
import math
import re
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

def generate_ai_script(format_type, duration_sec, topic):
    # 1 Scene = approx 4 seconds of dialogue
    target_scenes = max(3, math.ceil(int(duration_sec) / 4))
    
    system_prompt = "You are a Master Visual Storyteller and Comedy Writer. Output strictly in the requested format."
    
    user_prompt = f"""Task: Create a highly engaging, FUNNY, and HAPPY YouTube {format_type} story about: "{topic}".
    Total Scenes: EXACTLY {target_scenes}.

    🚨 STRICT RULES (CRITICAL):
    1. NO FEAR, NO SADNESS, NO HORROR. Only Comedy, Hardwork, Happiness, and Positive vibes.
    2. THE HOOK: The VERY FIRST dialogue must be super funny or shocking to make viewers stay 100%.
    3. CHARACTER CONSISTENCY: Keep the visual description of the main character EXACTLY the same in every prompt.
    4. DIALOGUE LENGTH: Each dialogue must be short (maximum 10-15 words) so it fits in 4 seconds.

    OUTPUT FORMAT MUST BE EXACTLY LIKE THIS (Visual Prompt | Dialogue):
    A funny yellow car with big cartoon eyes in a bright city street | अरे भई! तुमने इंसानों को बोलते देखा होगा, पर मैं हूँ दुनिया की पहली बक-बक करने वाली कार!
    A funny yellow car with big cartoon eyes laughing near a traffic light | लोग मुझे देखकर ऐसे घूरते हैं जैसे मैंने कोई जोक मार दिया हो!

    START DIRECTLY WITH SCENE 1:"""
    
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-lite-preview-02-05:free",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.8
        )
        text = response.choices[0].message.content
        
        valid_lines = [line.strip() for line in text.split('\n') if '|' in line and not line.startswith('-')]
        return "\n".join(valid_lines[:target_scenes])
    except Exception as e:
        print(f"Error: {e}")
        return None

def generate_ai_metadata(topic, format_type):
    tag_style = "#shorts, #trending, #comedy" if format_type == "SHORT" else "funny story, moral story, comedy video, entertaining"
    prompt = f"Topic: '{topic}'. Format: {format_type}.\nCreate viral Title, Description, and Tags (comma separated).\nFormat:\nTITLE: [Title]\nDESC: [Desc]\nTAGS: [Tags]"
    
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-lite-preview-02-05:free",
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.choices[0].message.content
        title = re.search(r"TITLE:\s*(.*)", text).group(1).strip()
        desc = re.search(r"DESC:\s*([\s\S]*?)TAGS:", text).group(1).strip()
        tags = re.search(r"TAGS:\s*(.*)", text).group(1).strip()
        return title, desc, tags
    except:
        return f"Funny {topic}", "Enjoy this funny story!", tag_style

def process_stories():
    with open(STORY_FILE, "r", encoding="utf-8") as f: content = f.read().strip()
    topics = [t.strip() for t in content.split("\n") if t.strip()]
    
    parts = topics[0].split("|")
    format_type = parts[0].strip().upper()
    duration_sec = int(parts[1].strip())
    topic = parts[2].strip()
    
    # Save Format for FFmpeg to know (Short/Long)
    with open("video_format.txt", "w") as f: f.write(format_type)

    ai_script = generate_ai_script(format_type, duration_sec, topic)
    with open(PROMPT_FILE, "w", encoding="utf-8") as f: f.write(ai_script + "\n")
    
    title, desc, tags = generate_ai_metadata(topic, format_type)
    with open(METADATA_FILE, "w", encoding="utf-8") as f: f.write(f"TITLE: {title}\nDESC: {desc}\nTAGS: {tags}")

if __name__ == "__main__":
    process_stories()
