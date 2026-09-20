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
    models_list = []
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
        models_list = [
            m["id"] for m in data.get("data", [])
            if m.get("pricing", {}).get("prompt") == "0"
            and m.get("pricing", {}).get("completion") == "0"
        ]
        print(f"✅ Live Free Models Found: {len(models_list)}")
    except Exception as e:
        print(f"⚠️ Could not fetch live models: {e}")

    fallbacks = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
        "mistralai/mistral-nemo:free",
        "meta-llama/llama-3.2-3b-instruct:free"
    ]
    for fb in fallbacks:
        if fb not in models_list:
            models_list.append(fb)
    return models_list

def generate_ai_script(format_type, duration_sec, topic):
    target_scenes = max(3, math.ceil(int(duration_sec) / 4))

    system_prompt = """You are a World-Class Visual Storyteller, Comedy Writer, and YouTube Retention Expert.
You strictly follow the output format. You write ONLY the scene lines. No extra text."""

    user_prompt = f"""Create a {format_type} YouTube story about: "{topic}"
Total Scenes: EXACTLY {target_scenes}

STRICT RULES:
1. Story must be FUNNY, HAPPY, POSITIVE. No fear, no sadness, no violence.
2. Scene 1 MUST be a HOOK - so funny or surprising that no one can scroll away.
3. Every scene must connect to the previous one like a real story (not random scenes).
4. ONE main character - describe them EXACTLY THE SAME in every image prompt.
5. Image prompt must be in English, detailed, cinematic, cartoon-style if funny.
6. Video prompt must describe MOVEMENT only (camera moves, character action).
7. Dialogue must be in Hindi, short (max 12 words), punchy, and match the scene exactly.

OUTPUT FORMAT (3 parts separated by | symbol):
[Detailed English Image Prompt] | [Short English Video Motion Prompt] | [Hindi Dialogue for Voiceover]

EXAMPLE:
A cheerful tiny red ant named Chhotu wearing a yellow hard hat, standing at the base of a giant mountain, looking up with wide excited eyes, bright sunny day, cartoon style | Camera slowly zooms out revealing the massive mountain, ant looks tiny, motivational feel | अरे! यह पहाड़ उठाना है? कोई बात नहीं, मैं Chhotu हूँ!
A cheerful tiny red ant named Chhotu wearing a yellow hard hat, pushing a huge boulder uphill with all his might, sweat drops, determined face, cartoon style | Camera follows the ant from behind, slow cinematic push, dust particles flying | हाँ भाई! थकान तो होगी, पर हार नहीं मानूँगा!

NOW WRITE {target_scenes} SCENES FOR: "{topic}"
START DIRECTLY WITH SCENE 1:"""

    models = get_live_free_models()
    attempt = 1
    max_attempts = 10

    for model_name in models:
        for _ in range(2):
            if attempt > max_attempts:
                print("❌ All 10 attempts failed.")
                return None

            print(f"🔄 Attempt {attempt}/{max_attempts} | Model: {model_name}")
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.85
                )
                text = response.choices[0].message.content

                if text:
                    print(f"\n📝 RAW AI OUTPUT:\n{text}\n")
                    valid_lines = []
                    for line in text.split('\n'):
                        line = line.strip()
                        line = re.sub(r'^[\d\.\-\*\#\s]+', '', line)
                        if line.count('|') >= 2:
                            parts = line.split('|')
                            img = parts[0].strip()
                            vid = parts[1].strip()
                            dlg = parts[2].strip()
                            if len(img) > 10 and len(vid) > 5 and len(dlg) > 3:
                                valid_lines.append(f"{img} | {vid} | {dlg}")

                    if len(valid_lines) >= 2:
                        print(f"✅ {len(valid_lines)} valid scenes generated!")
                        return "\n".join(valid_lines[:target_scenes])
                    else:
                        print("⚠️ Not enough valid lines. Retrying...")

            except Exception as e:
                print(f"⚠️ Error: {e}")
                time.sleep(3)
            attempt += 1

    return None

def generate_ai_metadata(topic, format_type):
    if format_type == "SHORT":
        tag_style = "#shorts #trending #comedy #funny #viral"
    else:
        tag_style = "funny story hindi, moral story, comedy video, viral story"

    prompt = f"""You are a YouTube SEO Expert. Topic: '{topic}'. Format: {format_type}.
Create viral metadata. Format EXACTLY:
TITLE: [Clickbait funny title in Hindi, max 60 chars]
DESC: [2-3 lines description in Hindi with emojis]
TAGS: [10 comma separated tags]
MUSIC: [5-7 word English music mood description]"""

    models = get_live_free_models()
    for model_name in models[:4]:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9
            )
            text = response.choices[0].message.content
            title = re.search(r"TITLE:\s*(.*)", text).group(1).strip()
            desc = re.search(r"DESC:\s*([\s\S]*?)TAGS:", text).group(1).strip()
            tags = re.search(r"TAGS:\s*(.*)", text).group(1).strip()
            music = re.search(r"MUSIC:\s*(.*)", text).group(1).strip()
            with open("music_prompt.txt", "w", encoding="utf-8") as f:
                f.write(music)
            print(f"✅ Metadata generated using {model_name}")
            return title, desc, tags
        except Exception as e:
            print(f"⚠️ Metadata attempt failed: {e}")
            time.sleep(1)

    with open("music_prompt.txt", "w") as f:
        f.write("happy funny upbeat comedy background music")
    return f"😂 {topic[:50]}", "देखो इस मज़ेदार कहानी को! 😂🔥", tag_style

def process_stories():
    print("🚀 Starting Auto Prompt Generation...")

    if not os.path.exists(STORY_FILE):
        print(f"❌ ERROR: {STORY_FILE} not found!")
        sys.exit(1)

    with open(STORY_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        print(f"❌ ERROR: {STORY_FILE} is empty!")
        sys.exit(1)

    topics = [t.strip() for t in content.split("\n") if t.strip()]
    print(f"📋 Total stories in queue: {len(topics)}")

    first_line = topics[0]
    parts = first_line.split("|")

    if len(parts) == 3:
        format_type = parts[0].strip().upper()
        duration_sec = int(re.search(r'\d+', parts[1]).group())
        topic = parts[2].strip()
    elif len(parts) == 2:
        duration_sec = int(re.search(r'\d+', parts[0]).group())
        topic = parts[1].strip()
        format_type = "SHORT"
    else:
        duration_sec = 30
        topic = first_line
        format_type = "SHORT"

    print(f"🎬 Format: {format_type} | Duration: {duration_sec}s | Topic: {topic}")
    with open("video_format.txt", "w") as f:
        f.write(format_type)

    ai_output = generate_ai_script(format_type, duration_sec, topic)
    if not ai_output:
        print("❌ CRITICAL: Script generation failed!")
        sys.exit(1)

    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        f.write(ai_output + "\n")
    print(f"✅ prompts.txt saved!")

    title, desc, tags = generate_ai_metadata(topic, format_type)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        f.write(f"TITLE: {title}\nDESC: {desc}\nTAGS: {tags}")
    print(f"✅ metadata.txt saved!")

    remaining = topics[1:]
    with open(STORY_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(remaining) + "\n" if remaining else "")
    print(f"📋 Remaining stories: {len(remaining)}")
    print("🎉 auto_prompt.py completed successfully!")

if __name__ == "__main__":
    process_stories()
