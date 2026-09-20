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
    print("❌ ERROR: OPENROUTER_API_KEY is missing!")
    sys.exit(1)

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

def get_live_free_models():
    # यह फंक्शन OpenRouter से खुद-ब-खुद बेस्ट फ्री मॉडल्स ढूंढ कर लाएगा
    models_list = []
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
        models_list = [m["id"] for m in data.get("data", []) if m.get("pricing", {}).get("prompt") == "0" and m.get("pricing", {}).get("completion") == "0"]
    except:
        print("⚠️ Warning: Could not fetch live models. Using Fallbacks.")
        pass
        
    # Guaranteed Fallback Models (अगर API से लिस्ट न मिले)
    fallbacks = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.0-flash-lite-preview-02-05:free", 
        "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
        "meta-llama/llama-3.2-3b-instruct:free"
    ]
    
    # दोनों लिस्ट्स को कंबाइन कर देते हैं
    for fb in fallbacks:
        if fb not in models_list:
            models_list.append(fb)
            
    return models_list

def generate_ai_script(format_type, duration_sec, topic):
    # 1 सीन का डायलॉग लगभग 4 सेकंड का होगा
    target_scenes = max(3, math.ceil(int(duration_sec) / 4))
    
    system_prompt = "You are a Master Visual Storyteller and Comedy Writer. You strictly follow instructions. Output ONLY the raw prompt lines. NO tables, NO intro."
    
    user_prompt = f"""Task: Create a highly engaging, FUNNY, and HAPPY YouTube {format_type} story about: "{topic}".
    Total Scenes: EXACTLY {target_scenes}.

    🚨 STRICT RULES (CRITICAL):
    1. NO FEAR, NO SADNESS, NO HORROR. Only Comedy, Hardwork, Happiness, and Positive vibes.
    2. THE HOOK: The VERY FIRST dialogue must be super funny or shocking to make viewers stay 100%.
    3. CHARACTER CONSISTENCY: Keep the visual description of the main character EXACTLY the same in every prompt.
    4. DIALOGUE LENGTH: Each dialogue must be short (maximum 10-15 words) so it fits in 4 seconds.

    OUTPUT FORMAT MUST BE EXACTLY LIKE THIS (Use the `|` symbol):
    [Visual Image Prompt in English] | [Funny Dialogue for Voiceover]
    
    EXAMPLE:
    A funny yellow car with big cartoon eyes in a bright city street | अरे भई! तुमने इंसानों को बोलते देखा होगा, पर मैं हूँ दुनिया की पहली बक-बक करने वाली कार!
    A funny yellow car with big cartoon eyes laughing near a traffic light | लोग मुझे देखकर ऐसे घूरते हैं जैसे मैंने कोई जोक मार दिया हो!

    START DIRECTLY WITH SCENE 1:"""
    
    models = get_live_free_models()
    attempt = 1
    max_attempts = 10 # स्क्रिप्ट जब तक नहीं बनेगी, 10 बार तक अलग-अलग मॉडल ट्राई करेगा!

    for model_name in models:
        for _ in range(2): # एक मॉडल को 2 बार मौका देगा
            if attempt > max_attempts:
                print("❌ ERROR: 10 attempts हो गए पर किसी AI ने सही फॉर्मेट नहीं दिया। Exiting.")
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
                    valid_lines = []
                    for line in text.split('\n'):
                        line = line.strip()
                        line = re.sub(r'^[\d\.\-\*\s]+', '', line) # गलती से आए नंबर्स हटाएगा
                        if '|' in line and '---|' not in line and not line.startswith('|'):
                            valid_lines.append(line)
                            
                    if len(valid_lines) > 0:
                        print(f"✅ Success! हमें {len(valid_lines)} valid scenes मिल गए from {model_name}.")
                        return "\n".join(valid_lines[:target_scenes])
                    else:
                        print(f"⚠️ AI ने स्क्रिप्ट दी, पर फॉर्मेट गलत था (No `|` found). Retrying...")
            except Exception as e:
                print(f"⚠️ Model {model_name} failed/crashed: {e}. Switching model...")
                time.sleep(2)
                
            attempt += 1

    return None

def generate_ai_metadata(topic, format_type):
    tag_style = "#shorts, #trending, #comedy" if format_type == "SHORT" else "funny story, moral story, comedy video, entertaining"
    system_prompt = "You are a highly creative YouTube SEO Expert."
    user_prompt = f"""Story Topic: '{topic}'. Format: {format_type}.
    Create Advertiser-Friendly YouTube metadata.
    Format EXACTLY like this:
    TITLE: [Viral Title]
    DESC: [Description]
    TAGS: [tag1, tag2, tag3]"""
    
    models = get_live_free_models()
    
    for model_name in models[:3]: # शुरू के 3 मॉडल्स को ट्राई करेगा
        try:
            print(f"🎵 Generating Metadata using {model_name}...")
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.8
            )
            text = response.choices[0].message.content
            
            title = re.search(r"TITLE:\s*(.*)", text).group(1).strip()
            desc = re.search(r"DESC:\s*([\s\S]*?)TAGS:", text).group(1).strip()
            tags = re.search(r"TAGS:\s*(.*)", text).group(1).strip()
            
            print("✅ Metadata successfully generated!")
            return title, desc, tags
        except:
            time.sleep(1)
            
    # अगर सब फेल हो जाएं तो डिफ़ॉल्ट दे दो (ताकि क्रैश न हो)
    return f"Funny Story about {topic} 😂", "Watch this amazing funny story!", tag_style

def process_stories():
    if not os.path.exists(STORY_FILE):
        print(f"❌ ERROR: {STORY_FILE} file not found!")
        sys.exit(1)
        
    with open(STORY_FILE, "r", encoding="utf-8") as f: content = f.read().strip()
    
    if not content:
        print(f"❌ ERROR: {STORY_FILE} is empty!")
        sys.exit(1)
        
    topics = [t.strip() for t in content.split("\n") if t.strip()]
    
    # Format parsing: SHORT | 30 | फनी कुत्ता जो पिज़्ज़ा बनाता है
    parts = topics[0].split("|")
    format_type = parts[0].strip().upper() if len(parts) > 0 else "SHORT"
    duration_sec = int(parts[1].strip()) if len(parts) > 1 else 30
    topic = parts[2].strip() if len(parts) > 2 else topics[0]
    
    print(f"📝 Format: {format_type}, Time: {duration_sec}s, Topic: {topic}")
    
    # FFmpeg एडिटिंग के लिए फॉर्मेट सेव करना
    with open("video_format.txt", "w") as f: f.write(format_type)

    ai_output = generate_ai_script(format_type, duration_sec, topic)
    
    if not ai_output:
        print("❌ CRITICAL ERROR: 10 attempts के बाद भी AI fail हो गया. Process stopped.")
        sys.exit(1)
        
    with open(PROMPT_FILE, "w", encoding="utf-8") as f: f.write(ai_output + "\n")
    
    title, desc, tags = generate_ai_metadata(topic, format_type)
    with open(METADATA_FILE, "w", encoding="utf-8") as f: f.write(f"TITLE: {title}\nDESC: {desc}\nTAGS: {tags}")
    
    # प्रोसेस की हुई स्टोरी को हटाकर बाकी सेव कर दो
    with open(STORY_FILE, "w", encoding="utf-8") as f: f.write("\n".join(topics[1:]) + "\n" if len(topics) > 1 else "")
    print("🚀 All processes completed successfully!")

if __name__ == "__main__":
    process_stories()
