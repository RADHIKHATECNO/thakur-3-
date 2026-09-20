import os
import sys
import math
import re
from openai import OpenAI

STORY_FILE = "story.txt"
PROMPT_FILE = "prompts.txt"
METADATA_FILE = "metadata.txt"

API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    print("❌ ERROR: OPENROUTER_API_KEY is missing!")
    sys.exit(1)

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

# 🚀 4 Best Free Models (एक फेल होगा तो दूसरा अपने आप चलेगा)
MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
    "mistralai/mistral-nemo:free"
]

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
    
    for model_name in MODELS:
        print(f"🔄 Trying AI Model: {model_name}...")
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.8
            )
            text = response.choices[0].message.content
            
            # Output को साफ़ करना (सिर्फ़ | वाली लाइन्स लेना)
            valid_lines = [line.strip() for line in text.split('\n') if '|' in line and not line.startswith('-')]
            
            if len(valid_lines) > 0:
                print(f"✅ Success! Script generated using {model_name}")
                return "\n".join(valid_lines[:target_scenes])
            else:
                print(f"⚠️ Model {model_name} gave wrong format. Trying next...")
                
        except Exception as e:
            print(f"⚠️ Model {model_name} Failed: {e}")
            
    return None

def generate_ai_metadata(topic, format_type):
    tag_style = "#shorts, #trending, #comedy" if format_type == "SHORT" else "funny story, moral story, comedy video, entertaining"
    prompt = f"Topic: '{topic}'. Format: {format_type}.\nCreate viral Title, Description, and Tags (comma separated).\nFormat:\nTITLE: [Title]\nDESC: [Desc]\nTAGS: [Tags]"
    
    for model_name in MODELS[:2]: # शुरू के 2 मॉडल्स में ट्राई करेगा
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.choices[0].message.content
            title = re.search(r"TITLE:\s*(.*)", text).group(1).strip()
            desc = re.search(r"DESC:\s*([\s\S]*?)TAGS:", text).group(1).strip()
            tags = re.search(r"TAGS:\s*(.*)", text).group(1).strip()
            return title, desc, tags
        except:
            continue
            
    # अगर सब फेल हो जाएं तो डिफ़ॉल्ट दे दो (ताकि क्रैश न हो)
    return f"Funny Story about {topic}", "Enjoy this funny and amazing story!", tag_style

def process_stories():
    if not os.path.exists(STORY_FILE):
        print(f"❌ ERROR: {STORY_FILE} not found!")
        sys.exit(1)
        
    with open(STORY_FILE, "r", encoding="utf-8") as f: content = f.read().strip()
    
    if not content:
        print("❌ ERROR: story.txt is empty!")
        sys.exit(1)
        
    topics = [t.strip() for t in content.split("\n") if t.strip()]
    
    parts = topics[0].split("|")
    format_type = parts[0].strip().upper() if len(parts) > 0 else "SHORT"
    duration_sec = int(parts[1].strip()) if len(parts) > 1 else 30
    topic = parts[2].strip() if len(parts) > 2 else topics[0]
    
    # FFmpeg के लिए फॉर्मेट सेव करना
    with open("video_format.txt", "w") as f: f.write(format_type)

    # 1. Script बनाना
    ai_script = generate_ai_script(format_type, duration_sec, topic)
    
    # 🔴 ERROR FIX: अगर सारी APIs फेल हो जाएं तो कोड क्रैश न हो बल्कि रुक जाए
    if not ai_script:
        print("❌ CRITICAL ERROR: All AI Models failed to generate script. Stopping process.")
        sys.exit(1)
        
    with open(PROMPT_FILE, "w", encoding="utf-8") as f: f.write(ai_script + "\n")
    
    # 2. Metadata बनाना
    title, desc, tags = generate_ai_metadata(topic, format_type)
    with open(METADATA_FILE, "w", encoding="utf-8") as f: f.write(f"TITLE: {title}\nDESC: {desc}\nTAGS: {tags}")

if __name__ == "__main__":
    process_stories()
