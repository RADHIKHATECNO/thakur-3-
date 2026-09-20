import os
import sys
import math
import re
import time
import json
import urllib.request
from openai import OpenAI

# ============================================================
# FILES
# ============================================================
STORY_FILE    = "story.txt"
PROMPT_FILE   = "prompts.txt"
METADATA_FILE = "metadata.txt"
MUSIC_FILE    = "music_prompt.txt"
CONFIG_FILE   = "video_config.json"  # Short/Long config save hoga

# ============================================================
# API SETUP
# ============================================================
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    print("❌ ERROR: OPENROUTER_API_KEY missing!")
    sys.exit(1)

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

# ============================================================
# FREE MODELS FETCH
# ============================================================
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
    except:
        pass

    fallbacks = [
        "google/gemini-2.0-flash-lite-preview-02-05:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
        "meta-llama/llama-3.2-3b-instruct:free"
    ]
    for fb in fallbacks:
        if fb not in models_list:
            models_list.append(fb)

    return models_list

# ============================================================
# STORY FORMAT PARSER
# ============================================================
def parse_story_line(line):
    """
    Format: short | 30sec | topic - comedy
            long  | 10min | topic - comedy
    Returns: (video_type, duration_sec, topic)
    """
    parts = [p.strip() for p in line.split("|")]

    if len(parts) < 3:
        # Old format fallback: 30 | topic
        try:
            duration_sec = int(re.search(r'\d+', parts[0]).group())
            topic = parts[1].strip() if len(parts) > 1 else parts[0]
            return "short", duration_sec, topic
        except:
            return "short", 30, line.strip()

    video_type = parts[0].lower().strip()  # short ya long
    time_str   = parts[1].lower().strip()  # 30sec, 10min etc
    topic      = parts[2].strip()          # actual topic

    # Duration calculate karna
    if "min" in time_str:
        minutes = int(re.search(r'\d+', time_str).group())
        duration_sec = minutes * 60
    else:
        duration_sec = int(re.search(r'\d+', time_str).group())

    return video_type, duration_sec, topic

# ============================================================
# SCENE COUNT CALCULATOR
# ============================================================
def calculate_scenes(video_type, duration_sec):
    if video_type == "short":
        # Shorts: har 5 sec pe 1 scene
        return max(3, math.ceil(duration_sec / 5))
    else:
        # Long: har 8 sec pe 1 scene
        return max(10, math.ceil(duration_sec / 8))

# ============================================================
# CHARACTER GENERATOR
# ============================================================
def generate_character(topic):
    """
    Topic se ek unique consistent character banao
    Jo poori video mein same rahe
    """
    system = "You are a creative character designer. Give ONE character description in exactly 1 line. Be specific about appearance."
    prompt = f"""Based on this story topic: '{topic}'
    
Create ONE unique funny main character with:
- Exact name
- Exact appearance (color, size, clothing, expression)
- One funny personality trait

Format: [Name] - [exact appearance] - [funny trait]
Example: Chotu the Car - shiny red body with big googly eyes and a bent antenna - always complaining loudly

ONE LINE ONLY:"""

    models = get_live_free_models()
    for model in models[:3]:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9
            )
            char = response.choices[0].message.content.strip().split('\n')[0]
            if char and len(char) > 10:
                print(f"✅ Character Created: {char}")
                return char
        except:
            time.sleep(1)

    # Fallback character
    return "Raju - a small round orange robot with big blinking eyes and tiny wheels - always trips but never gives up"

# ============================================================
# HINDI NARRATION SCRIPT GENERATOR
# ============================================================
def generate_narration_script(video_type, duration_sec, topic, character, scene_count):
    """
    Har scene ke liye Hindi narration banao
    Jo exactly visual se match kare
    """
    system = """You are a master Hindi storyteller and narrator. 
    You write EXACTLY what is happening on screen in energetic Hindi.
    Your narration must match the visual 100%.
    Output ONLY narration lines. No extra text."""

    if video_type == "short":
        words_per_scene = 20  # ~4 seconds of speech
    else:
        words_per_scene = 80  # ~16 seconds of speech

    prompt = f"""Story Topic: '{topic}'
Main Character: {character}
Total Scenes: {scene_count}
Style: FUNNY, ENERGETIC, HAPPY - No fear, no horror, no sadness

Write EXACTLY {scene_count} Hindi narration lines.
Each line = what narrator says while THAT scene plays on screen.
Must be energetic, funny, and match the visual action perfectly.

RULES:
- Line 1 = SUPER HOOK - most exciting moment to grab attention
- Every line must describe EXACTLY what character is doing
- Use funny expressions: "Arrey!", "Waah!", "Oho!", "Haha!"
- Each line max {words_per_scene} words
- Hindi only (Devanagari script)
- NO English words
- End with satisfying conclusion

FORMAT (use | separator):
[Scene visual description in English] | [Hindi narration text]

Example:
Raju robot slipping on banana peel with shocked face | अरे! राजू भाई फिसल गए केले के छिलके पर, और उनका चेहरा देखो - एकदम गोल आँखें!

START DIRECTLY:"""

    models = get_live_free_models()
    max_attempts = 10

    for attempt, model in enumerate(models, 1):
        if attempt > max_attempts:
            break
        for retry in range(2):
            print(f"🔄 Narration Attempt {attempt} - Model: {model}")
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.85
                )
                text = response.choices[0].message.content.strip()

                # Valid lines filter karo
                valid = []
                for line in text.split('\n'):
                    line = line.strip()
                    line = re.sub(r'^[\d\.\-\*\s]+', '', line)
                    if '|' in line and len(line) > 20:
                        parts = line.split('|')
                        if len(parts) >= 2 and len(parts[1].strip()) > 5:
                            valid.append(line)

                if len(valid) >= scene_count * 0.7:  # 70% scenes mil gaye
                    print(f"✅ Got {len(valid)} narration scenes!")
                    return valid[:scene_count]
                else:
                    print(f"⚠️ Only {len(valid)} valid lines. Retrying...")

            except Exception as e:
                print(f"⚠️ Model {model} failed: {e}")
                time.sleep(2)

    return None

# ============================================================
# VIRAL METADATA GENERATOR
# ============================================================
def generate_viral_metadata(video_type, topic, character):
    system = "You are a YouTube viral growth expert. Create metadata that gets maximum clicks and views."

    if video_type == "short":
        format_hint = "YouTube Shorts (vertical 9:16, under 60 seconds)"
        title_style = "Short punchy title with emoji, max 60 chars"
    else:
        format_hint = "YouTube Long Video (horizontal 16:9, 10-20 minutes)"
        title_style = "Engaging long-form title with keywords, max 70 chars"

    prompt = f"""Topic: '{topic}'
Character: {character}
Format: {format_hint}
Mood: Funny, Happy, Energetic, Family-Friendly

Create VIRAL YouTube metadata:

TITLE: [{title_style}]
DESC: [2-3 lines, funny hook, includes character name, ends with subscribe CTA]
TAGS: [15 viral Hindi comedy tags, comma separated]
MUSIC: [5-7 word upbeat funny background music description]

Rules:
- Title must make people CLICK immediately
- Description first line = strongest hook
- Tags mix: Hindi + English comedy tags
- All family friendly, advertiser safe"""

    models = get_live_free_models()
    default_music = "upbeat funny cartoon comedy background music"

    for model in models[:4]:
        try:
            print(f"📊 Metadata generation - Model: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.85
            )
            text = response.choices[0].message.content

            title   = re.search(r"TITLE:\s*(.*)", text).group(1).strip()
            desc    = re.search(r"DESC:\s*([\s\S]*?)TAGS:", text).group(1).strip()
            tags    = re.search(r"TAGS:\s*(.*)", text).group(1).strip()
            music   = re.search(r"MUSIC:\s*(.*)", text).group(1).strip()

            with open(MUSIC_FILE, "w", encoding="utf-8") as f:
                f.write(music)

            print("✅ Viral Metadata Generated!")
            return title, desc, tags

        except Exception as e:
            print(f"⚠️ Metadata model {model} failed: {e}")
            time.sleep(1)

    # Fallback
    with open(MUSIC_FILE, "w", encoding="utf-8") as f:
        f.write(default_music)
    return "😂 Funny Story Jo Aapko Hasaegi!", "Ek mazedaar kahani sunne ke liye tayaar ho jao!", "funny, comedy, hindi, shorts, viral"

# ============================================================
# MAIN PIPELINE
# ============================================================
def process_stories():
    # Story file check
    if not os.path.exists(STORY_FILE):
        print(f"❌ {STORY_FILE} not found!")
        sys.exit(1)

    with open(STORY_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        print(f"❌ {STORY_FILE} is empty!")
        sys.exit(1)

    topics = [t.strip() for t in content.split("\n") if t.strip()]
    current_line = topics[0]

    print(f"\n{'='*50}")
    print(f"📖 Processing: {current_line}")
    print(f"{'='*50}\n")

    # Parse format
    video_type, duration_sec, topic = parse_story_line(current_line)
    scene_count = calculate_scenes(video_type, duration_sec)

    print(f"📺 Video Type : {video_type.upper()}")
    print(f"⏱️  Duration   : {duration_sec} seconds")
    print(f"🎬 Scenes     : {scene_count}")
    print(f"📝 Topic      : {topic}\n")

    # Step 1: Character banao
    print("👤 Creating consistent character...")
    character = generate_character(topic)

    # Step 2: Narration + Visual prompts banao
    print("\n📝 Generating narration + visual script...")
    script_lines = generate_narration_script(
        video_type, duration_sec, topic, character, scene_count
    )

    if not script_lines:
        print("❌ Script generation failed after all attempts!")
        sys.exit(1)

    # Step 3: prompts.txt save karo
    # Format: visual_prompt | narration_hindi
    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        for line in script_lines:
            f.write(line.strip() + "\n")

    print(f"\n✅ {len(script_lines)} scenes written to {PROMPT_FILE}")

    # Step 4: Video config save karo (baaki files use karengi)
    config = {
        "video_type": video_type,
        "duration_sec": duration_sec,
        "topic": topic,
        "character": character,
        "scene_count": len(script_lines),
        "aspect_ratio": "9:16" if video_type == "short" else "16:9"
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"✅ Video config saved: {config}")

    # Step 5: Viral Metadata banao
    print("\n🚀 Generating viral metadata...")
    title, desc, tags = generate_viral_metadata(video_type, topic, character)

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        f.write(f"TITLE: {title}\n")
        f.write(f"DESC: {desc}\n")
        f.write(f"TAGS: {tags}\n")
        f.write(f"VIDEO_TYPE: {video_type}\n")

    print(f"\n{'='*50}")
    print(f"🎉 ALL DONE!")
    print(f"   Title     : {title}")
    print(f"   Character : {character}")
    print(f"   Scenes    : {len(script_lines)}")
    print(f"{'='*50}\n")

    # Step 6: Used story remove karo
    remaining = topics[1:]
    with open(STORY_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(remaining) + "\n" if remaining else "")

    print("🚀 Pipeline Stage 1 Complete!")

if __name__ == "__main__":
    process_stories()
