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
CONFIG_FILE   = "video_config.json"

# ============================================================
# API SETUP
# ============================================================
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    print("❌ ERROR: OPENROUTER_API_KEY missing!")
    sys.exit(1)

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

# ============================================================
# FREE MODELS
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
# STORY PARSER
# ============================================================
def parse_story_line(line):
    """
    Format: short | 30sec | topic - comedy
            long  | 10min | topic - comedy
    """
    parts = [p.strip() for p in line.split("|")]

    if len(parts) < 3:
        try:
            duration_sec = int(re.search(r'\d+', parts[0]).group())
            topic = parts[1].strip() if len(parts) > 1 else parts[0]
            return "short", duration_sec, topic
        except:
            return "short", 30, line.strip()

    video_type   = parts[0].lower().strip()
    time_str     = parts[1].lower().strip()
    topic        = parts[2].strip()

    if "min" in time_str:
        minutes      = int(re.search(r'\d+', time_str).group())
        duration_sec = minutes * 60
    else:
        duration_sec = int(re.search(r'\d+', time_str).group())

    return video_type, duration_sec, topic

# ============================================================
# SCENE CALCULATOR
# ============================================================
def calculate_scenes(video_type, duration_sec):
    if video_type == "short":
        return max(3, math.ceil(duration_sec / 5))
    else:
        return max(10, math.ceil(duration_sec / 8))

# ============================================================
# VISUAL STYLE DETECTOR
# ============================================================
def detect_visual_style(topic):
    """
    Topic se visual style detect karo
    """
    topic_lower = topic.lower()

    # Horror/Dark
    if any(w in topic_lower for w in [
        "horror", "dark", "ghost", "bhoot",
        "scary", "darr", "raat", "shaitan"
    ]):
        return "2D Anime dark style"

    # Realistic Human
    if any(w in topic_lower for w in [
        "human", "insaan", "aadmi", "ladka",
        "ladki", "realistic", "real"
    ]):
        return "Pixar 3D animation style"

    # Animal
    if any(w in topic_lower for w in [
        "animal", "janwar", "dog", "cat",
        "kutta", "billi", "tiger", "lion"
    ]):
        return "cute cartoon animal style"

    # Robot/Sci-fi
    if any(w in topic_lower for w in [
        "robot", "sci-fi", "future", "space",
        "alien", "machine"
    ]):
        return "futuristic 3D CGI style"

    # Default - Funny Cartoon
    return "Pixar 3D funny cartoon style"

# ============================================================
# CHARACTER GENERATOR
# ============================================================
def generate_character(topic, visual_style):
    """
    Topic se consistent character banao
    """
    system = (
        "You are a creative character designer. "
        "Give ONE character description in exactly 1 line."
    )

    prompt = f"""Topic: '{topic}'
Visual Style: {visual_style}

Create ONE unique main character with:
- Exact name (Hindi/funny name)
- Exact appearance (color, size, clothing, expression)
- One funny personality trait

Format: [Name] | [exact appearance in English for image generation] | [funny trait]
Example: Motu Singh | fat funny woman, bright orange saree, big round eyes, angry expression | always stuck in traffic

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
                print(f"✅ Character: {char}")
                return char
        except:
            time.sleep(1)

    return "Raju | small round funny man, blue shirt, big eyes, surprised expression | always does wrong things"

# ============================================================
# MAIN SCRIPT GENERATOR
# ============================================================
def generate_full_script(video_type, duration_sec, topic, character, scene_count):
    """
    Har scene ke liye 3 parts banao:
    1. Hindi Narration (voice ke liye)
    2. Image Prompt (Bing ke liye)
    3. Video Prompt (Upsampler ke liye)
    """

    # Character parts nikalo
    char_parts   = character.split("|")
    char_name    = char_parts[0].strip() if len(char_parts) > 0 else "Raju"
    char_looks   = char_parts[1].strip() if len(char_parts) > 1 else "funny cartoon character"
    char_trait   = char_parts[2].strip() if len(char_parts) > 2 else "always funny"

    visual_style = detect_visual_style(topic)

    # Aspect ratio
    if video_type == "short":
        aspect      = "vertical 9:16 composition"
        image_style = f"{visual_style}, {aspect}, bright colorful"
    else:
        aspect      = "horizontal 16:9 widescreen"
        image_style = f"{visual_style}, {aspect}, cinematic"

    system = """You are a master Hindi storyteller and YouTube Shorts expert.
You create EXACTLY formatted scripts with 3 parts per scene.
Output ONLY the scenes. No extra text. No numbering."""

    prompt = f"""Topic: '{topic}'
Character Name: {char_name}
Character Looks: {char_looks}
Character Trait: {char_trait}
Visual Style: {visual_style}
Image Style: {image_style}
Total Scenes: {scene_count}
Mood: FUNNY, HAPPY, ENERGETIC - No horror, no sadness, no fear

Create EXACTLY {scene_count} scenes.

RULES:
- Scene 1 = SUPER HOOK (most exciting moment)
- Same character {char_name} in EVERY scene
- Hindi narration = energetic, funny, use "Arrey!", "Waah!", "Oho!"
- Image prompt = detailed English description for AI image generation
- Video prompt = camera movement + sound effects description
- Story must match 100% - visual and narration same cheez

FORMAT (use >> to separate 3 parts):
[Hindi narration] >> [Detailed image prompt in English] >> [Video motion + SFX prompt]

EXAMPLE:
अरे! मोटू सिंह ट्रैफिक में फंस गई! >> {visual_style}, {char_looks} named {char_name} stuck in heavy traffic jam, angry face, honking horn, bright colorful street, {aspect}, high quality >> Motu Singh honking loudly with shaking car, camera zoom in on angry face, SFX: loud horns, city noise, no bgm, no voice

START DIRECTLY WITH SCENE 1:"""

    models    = get_live_free_models()
    max_tries = 10

    for attempt, model in enumerate(models, 1):
        if attempt > max_tries:
            break
        for retry in range(2):
            print(f"🔄 Attempt {attempt} - Model: {model}")
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

                print("\n--- RAW OUTPUT ---")
                print(text[:300])
                print("------------------\n")

                # Valid lines filter
                valid = []
                for line in text.split('\n'):
                    line = line.strip()
                    line = re.sub(r'^[\d\.\-\*\s]+', '', line)
                    if '>>' in line:
                        parts = line.split('>>')
                        if len(parts) >= 3:
                            narration = parts[0].strip()
                            img_prompt = parts[1].strip()
                            vid_prompt = parts[2].strip()
                            if (len(narration) > 5 and
                                    len(img_prompt) > 10 and
                                    len(vid_prompt) > 10):
                                valid.append(line)

                if len(valid) >= scene_count * 0.7:
                    print(f"✅ Got {len(valid)} valid scenes!")
                    return valid[:scene_count]
                else:
                    print(f"⚠️ Only {len(valid)} valid. Retrying...")

            except Exception as e:
                print(f"⚠️ Model {model} failed: {e}")
                time.sleep(2)

    return None

# ============================================================
# METADATA GENERATOR
# ============================================================
def generate_viral_metadata(video_type, topic, character):
    system = "You are a YouTube viral growth expert."

    char_name = character.split("|")[0].strip()

    if video_type == "short":
        format_hint = "YouTube Shorts 9:16"
        title_style = "Short punchy Hindi title with emoji max 60 chars"
    else:
        format_hint = "YouTube Long Video 16:9"
        title_style = "Engaging Hindi title with keywords max 70 chars"

    prompt = f"""Topic: '{topic}'
Character: {char_name}
Format: {format_hint}
Mood: Funny, Happy, Family-Friendly

Create VIRAL YouTube metadata:
TITLE: [{title_style}]
DESC: [2-3 funny lines + subscribe CTA in Hindi]
TAGS: [15 viral Hindi comedy tags]
MUSIC: [5-7 word upbeat funny music description]"""

    models       = get_live_free_models()
    default_music = "upbeat funny cartoon comedy music"

    for model in models[:4]:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.85
            )
            text = response.choices[0].message.content

            title = re.search(r"TITLE:\s*(.*)", text).group(1).strip()
            desc  = re.search(
                r"DESC:\s*([\s\S]*?)(?:TAGS:|$)", text
            ).group(1).strip()
            tags  = re.search(r"TAGS:\s*(.*)", text).group(1).strip()
            music = re.search(r"MUSIC:\s*(.*)", text).group(1).strip()

            with open(MUSIC_FILE, "w", encoding="utf-8") as f:
                f.write(music)

            print("✅ Metadata generated!")
            return title, desc, tags

        except Exception as e:
            print(f"⚠️ Metadata failed: {e}")
            time.sleep(1)

    with open(MUSIC_FILE, "w", encoding="utf-8") as f:
        f.write(default_music)
    return (
        "😂 Funny Hindi Story!",
        "Ek mazedaar kahani!",
        "funny, comedy, hindi, shorts, viral"
    )

# ============================================================
# PROMPTS SAVER
# ============================================================
def save_prompts(script_lines):
    """
    prompts.txt mein save karo
    Format: NARRATION >> IMAGE_PROMPT >> VIDEO_PROMPT
    """
    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        for line in script_lines:
            f.write(line.strip() + "\n")

    print(f"✅ {len(script_lines)} scenes saved to prompts.txt")

    # Debug - pehla scene dikhao
    if script_lines:
        parts = script_lines[0].split(">>")
        print(f"\n📝 Scene 1 Preview:")
        print(f"   🎙️  Narration : {parts[0].strip()[:60]}...")
        if len(parts) > 1:
            print(f"   🎨 Image     : {parts[1].strip()[:60]}...")
        if len(parts) > 2:
            print(f"   🎬 Video     : {parts[2].strip()[:60]}...")

# ============================================================
# MAIN
# ============================================================
def process_stories():
    if not os.path.exists(STORY_FILE):
        print(f"❌ {STORY_FILE} not found!")
        sys.exit(1)

    with open(STORY_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        print(f"❌ {STORY_FILE} is empty!")
        sys.exit(1)

    topics      = [t.strip() for t in content.split("\n") if t.strip()]
    current     = topics[0]

    print(f"\n{'='*50}")
    print(f"📖 Processing: {current}")
    print(f"{'='*50}\n")

    video_type, duration_sec, topic = parse_story_line(current)
    scene_count  = calculate_scenes(video_type, duration_sec)
    visual_style = detect_visual_style(topic)

    print(f"📺 Type         : {video_type.upper()}")
    print(f"⏱️  Duration     : {duration_sec}s")
    print(f"🎬 Scenes       : {scene_count}")
    print(f"🎨 Visual Style : {visual_style}")
    print(f"📝 Topic        : {topic}\n")

    # Character banao
    print("👤 Creating character...")
    character = generate_character(topic, visual_style)

    # Script banao
    print("\n📝 Generating full script...")
    script_lines = generate_full_script(
        video_type, duration_sec, topic, character, scene_count
    )

    if not script_lines:
        print("❌ Script generation failed!")
        sys.exit(1)

    # Prompts save karo
    save_prompts(script_lines)

    # Config save karo
    config = {
        "video_type"   : video_type,
        "duration_sec" : duration_sec,
        "topic"        : topic,
        "character"    : character,
        "visual_style" : visual_style,
        "scene_count"  : len(script_lines),
        "aspect_ratio" : "9:16" if video_type == "short" else "16:9"
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✅ Config saved!")

    # Metadata banao
    print("\n🚀 Generating viral metadata...")
    title, desc, tags = generate_viral_metadata(
        video_type, topic, character
    )

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        f.write(f"TITLE: {title}\n")
        f.write(f"DESC: {desc}\n")
        f.write(f"TAGS: {tags}\n")
        f.write(f"VIDEO_TYPE: {video_type}\n")

    print(f"\n{'='*50}")
    print(f"🎉 STAGE 1 COMPLETE!")
    print(f"   Title     : {title}")
    print(f"   Character : {character[:50]}...")
    print(f"   Scenes    : {len(script_lines)}")
    print(f"{'='*50}\n")

    # Used story hatao
    remaining = topics[1:]
    with open(STORY_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(remaining) + "\n" if remaining else "")

if __name__ == "__main__":
    process_stories()
