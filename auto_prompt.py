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
    print("❌ ERROR: OPENROUTER_API_KEY is missing in GitHub Secrets!")
    sys.exit(1)

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

def get_live_free_models():
    models_list = []
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
        models_list = [m["id"] for m in data.get("data", []) if m.get("pricing", {}).get("prompt") == "0" and m.get("pricing", {}).get("completion") == "0"]
    except:
        pass
        
    fallbacks = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.0-flash-lite-preview-02-05:free", 
        "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
        "meta-llama/llama-3.2-3b-instruct:free"
    ]
    for fb in fallbacks:
        if fb not in models_list:
            models_list.append(fb)
    return models_list

def generate_ai_script(format_type, duration_sec, topic):
    target_scenes = max(3, math.ceil(int(duration_sec) / 4))
    system_prompt = "You are a Master Visual Storyteller and Comedy Writer. Output strictly in the requested format."
    
    user_prompt = f"""Task: Create a highly engaging, FUNNY, and HAPPY YouTube {format_type} story about: "{topic}".
    Total Scenes: EXACTLY {target_scenes}.

    🚨 STRICT RULES (CRITICAL):
    1. NO FEAR, NO SADNESS. Only Comedy, Happiness.
    2. THE HOOK: The VERY FIRST dialogue must be super funny or shocking.
    3. DIALOGUE LENGTH: Each dialogue must be short (maximum 10-15 words).

    OUTPUT FORMAT MUST HAVE EXACTLY 3 PARTS SEPARATED BY '|':
    [Bing Image Prompt] | [Upsampler Video Motion Prompt] | [Funny Dialogue for Voiceover]
    
    EXAMPLE FORMAT:
    A funny yellow car with big cartoon eyes in a bright city street | The car bouncing happily, cinematic slow motion | अरे भई! मैं हूँ दुनिया की पहली बक-बक करने वाली कार!
    A funny yellow car laughing near a traffic light | The car shaking and laughing, dynamic camera movement | लोग मुझे देखकर ऐसे घूरते हैं जैसे मैंने कोई जोक मार दिया हो!

    START DIRECTLY WITH SCENE 1 (No intro, No outro):"""
    
    models = get_live_free_models()
    attempt = 1
    max_attempts = 10

    for model_name in models:
        for _ in range(2): 
            if attempt > max_attempts:
                print("❌ ERROR: AI failed 10 attempts to give correct format.")
                return None
                
            print(f"🔄 Attempt {attempt}/{max_attempts} - Trying model: {model_name}...")
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    temperature=0.8
                )
                text = response.choices[0].message.content
                
                if text:
                    print(f"--- AI Raw Output ---\n{text}\n---------------------")
                    valid_lines = []
                    for line in text.split('\n'):
                        line = line.strip()
                        line = re.sub(r'^[\d\.\-\*\s]+', '', line)
                        # 🔴 FIX: कम से कम 2 बार '|' होना चाहिए
                        if line.count('|') >= 2:
                            valid_lines.append(line)
                            
                    if len(valid_lines) > 0:
                        print(f"✅ Success! {len(valid_lines)} valid scenes found.")
                        return "\n".join(valid_lines[:target_scenes])
                    else:
                        print(f"⚠️ AI ने फॉर्मेट गलत दिया (3 Parts नहीं मिले). Retrying...")
            except Exception as e:
                print(f"⚠️ Model failed: {e}. Switching...")
                time.sleep(2)
            attempt += 1
    return None

def generate_ai_metadata(topic, format_type):
    tag_style = "#shorts, #trending, #comedy" if format_type == "SHORT" else "funny story, moral story, comedy video, entertaining"
    prompt = f"Topic: '{topic}'. Format: {format_type}.\nFormat EXACTLY:\nTITLE: [Title]\nDESC: [Desc]\nTAGS: [tag1, tag2]"
    models = get_live_free_models()
    for model_name in models[:3]:
        try:
            response = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": prompt}])
            text = response.choices[0].message.content
            title = re.search(r"TITLE:\s*(.*)", text).group(1).strip()
            desc = re.search(r"DESC:\s*([\s\S]*?)TAGS:", text).group(1).strip()
            tags = re.search(r"TAGS:\s*(.*)", text).group(1).strip()
            return title, desc, tags
        except:
            time.sleep(1)
    return f"Funny Story about {topic} 😂", "Watch this amazing funny story!", tag_style

def process_stories():
    if not os.path.exists(STORY_FILE):
        print(f"❌ ERROR: {STORY_FILE} (story.txt) file not found in the main folder!")
        sys.exit(1)
        
    with open(STORY_FILE, "r", encoding="utf-8") as f: content = f.read().strip()
    if not content:
        print(f"❌ ERROR: {STORY_FILE} (story.txt) is completely empty! Please write a topic inside it.")
        sys.exit(1)
        
    topics = [t.strip() for t in content.split("\n") if t.strip()]
    parts = topics[0].split("|")
    format_type = parts[0].strip().upper() if len(parts) > 0 else "SHORT"
    duration_sec = int(parts[1].strip()) if len(parts) > 1 else 30
    topic = parts[2].strip() if len(parts) > 2 else topics[0]
    
    print(f"🎬 Processing: Format={format_type}, Time={duration_sec}s, Topic={topic}")
    with open("video_format.txt", "w") as f: f.write(format_type)

    ai_output = generate_ai_script(format_type, duration_sec, topic)
    if not ai_output:
        print("❌ ERROR: Could not generate valid AI script. Exiting.")
        sys.exit(1)
        
    with open(PROMPT_FILE, "w", encoding="utf-8") as f: f.write(ai_output + "\n")
    title, desc, tags = generate_ai_metadata(topic, format_type)
    with open(METADATA_FILE, "w", encoding="utf-8") as f: f.write(f"TITLE: {title}\nDESC: {desc}\nTAGS: {tags}")
    with open(STORY_FILE, "w", encoding="utf-8") as f: f.write("\n".join(topics[1:]) + "\n" if len(topics) > 1 else "")

if __name__ == "__main__":
    process_stories()
