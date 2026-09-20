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
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models"
        )
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

    print(f"✅ {len(models_list)} models available!")
    return models_list

# ============================================================
# STORY PARSER
# ============================================================
def parse_story_line(line):
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
        return max(4, math.ceil(duration_sec / 5))
    else:
        return max(15, math.ceil(duration_sec / 8))

# ============================================================
# VISUAL STYLE DETECTOR
# ============================================================
def detect_visual_style(topic):
    topic_lower = topic.lower()

    if any(w in topic_lower for w in [
        "animal", "janwar", "cat", "dog", "billi",
        "kutta", "mouse", "bird", "chidiya", "rabbit"
    ]):
        return "Tom and Jerry 2D cartoon animation style"

    if any(w in topic_lower for w in [
        "robot", "machine", "cyber", "future", "space"
    ]):
        return "funny Pixar 3D cartoon robot style"

    if any(w in topic_lower for w in [
        "car", "gaadi", "truck", "bus", "vehicle"
    ]):
        return "funny Pixar 3D cartoon vehicle style"

    # Default - Tom & Jerry like
    return "Tom and Jerry 2D cartoon animation style"

# ============================================================
# CHARACTER GENERATOR
# ============================================================
def generate_character(topic, visual_style):
    system = (
        "You are a cartoon character designer like Tom and Jerry creators. "
        "Create ONE very detailed funny cartoon character."
    )

    prompt = f"""Topic: '{topic}'
Visual Style: {visual_style}

Create ONE unique FUNNY cartoon character like Tom & Jerry style.

Include ALL details:
1. Funny name
2. Animal/creature type
3. Body (fat/thin/round/tall)
4. Color (exact colors)
5. Eyes (big/small/round/googly)
6. Clothing if any (exact colors)
7. Signature funny prop
8. Default expression
9. Funny running/moving style
10. Funny personality

Format EXACTLY:
NAME | [full detailed appearance in English] | [funny comedy trait]

Example:
Motu Cat | fat round orange tabby cat, huge googly yellow eyes, tiny pink nose, always wearing blue bow tie, stubby little legs, fluffy striped tail, default shocked wide-eye expression, runs in fast spinning legs cartoon style | thinks he is smartest but always fails hilariously

ONE LINE - Very detailed:"""

    models = get_live_free_models()
    for model in models[:4]:
        try:
            print(f"👤 Character - Model: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9
            )
            char = response.choices[0].message.content.strip()
            char = char.split('\n')[0].strip()
            char = re.sub(r'^[\d\.\-\*\s]+', '', char)

            if '|' in char and len(char) > 100:
                print(f"✅ Character: {char[:100]}...")
                return char
            else:
                print(f"⚠️ Too short, retrying...")

        except Exception as e:
            print(f"⚠️ Failed: {e}")
            time.sleep(1)

    # Detailed fallback
    return (
        "Raju Mouse | tiny chubby grey mouse, "
        "huge round black eyes, pink tiny nose, "
        "wearing red oversized hat and yellow polka dot shorts, "
        "white gloves, stubby tail, "
        "default mischievous grin expression, "
        "runs with fast spinning cartoon legs | "
        "always steals food but gets caught in funny ways"
    )

# ============================================================
# TOM & JERRY SCRIPT GENERATOR
# ============================================================
def generate_tom_jerry_script(
    video_type, duration_sec,
    topic, character, scene_count
):
    """
    Tom & Jerry style:
    - No dialogue
    - Pure visual comedy
    - Exaggerated expressions
    - Sound effects only
    - Funny actions
    """
    char_parts = character.split("|")
    char_name  = char_parts[0].strip()
    char_looks = char_parts[1].strip() if len(char_parts) > 1 else ""
    char_trait = char_parts[2].strip() if len(char_parts) > 2 else ""

    visual_style = detect_visual_style(topic)

    if video_type == "short":
        aspect = "vertical 9:16 composition"
    else:
        aspect = "horizontal 16:9 widescreen"

    full_char = f"{visual_style}, {char_looks}, named {char_name}"

    system = """You are a Tom & Jerry cartoon director.
You create PURE VISUAL COMEDY scenes.
NO dialogue. NO narration. ONLY actions and sound effects.
Output ONLY scene lines. Nothing else."""

    prompt = f"""Topic: '{topic}'
Character: {char_name}
Appearance: {char_looks}
Trait: {char_trait}
Style: {visual_style}
Total Scenes: {scene_count}
Mood: 100% FUNNY COMEDY - Like Tom & Jerry

Create EXACTLY {scene_count} scenes.

🎯 TOM & JERRY RULES:
- NO dialogue, NO voice, NO narration
- PURE visual comedy like cartoons
- Exaggerated expressions (eyes pop out, jaw drops, steam from ears)
- Funny physics (spinning legs, flat after rolling, stars after hit)
- Classic cartoon SFX (BOING! CRASH! WHOOSH! SPLAT! BONK!)
- Each scene = one funny action/reaction
- Building story - each scene connects to next
- Happy funny ending

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT (use >> separator):
[Image prompt] >> [Video motion prompt] >> [Sound effects list]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 IMAGE PROMPT RULES:
- Start with: "{full_char}"
- Add exact funny action
- Add exaggerated cartoon expression
- Add colorful background
- End with: {aspect}, bright vivid colors, high quality cartoon render, no text, no watermark
- MINIMUM 80 words

🔴 VIDEO PROMPT RULES:
- Camera movement (zoom/shake/pan)
- Character motion description
- Cartoon physics description
- Max 30 words

🔴 SOUND EFFECTS RULES:
- List 3-5 specific cartoon SFX
- Classic sounds: BOING, CRASH, WHOOSH, SPLAT, BONK, WHISTLE, SPRING, POP
- Timing description
- End with: upbeat cartoon bgm
- NO voice, NO dialogue

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERFECT EXAMPLE:
{full_char}, running at lightning speed with spinning cartoon legs, eyes wide with panic, tongue hanging out, chasing a giant rolling cheese wheel down a colorful hill, dust cloud behind, {aspect}, bright vivid colors, high quality cartoon render, no text, no watermark >> Fast tracking shot following character, legs spinning blur, dust cloud growing, zoom out to show giant cheese, cartoon speed lines >> WHOOSH fast run, BOING spring legs, RUMBLE rolling cheese, CRASH at bottom, upbeat cartoon bgm
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STORY STRUCTURE:
Scene 1: SUPER HOOK - Most shocking funny moment
Scene 2 to {scene_count-1}: Comedy escalates
Scene {scene_count}: Funny happy resolution

START WITH SCENE 1:"""

    models    = get_live_free_models()
    max_tries = 10

    for attempt, model in enumerate(models, 1):
        if attempt > max_tries:
            break
        for retry in range(2):
            print(f"🔄 Script Attempt {attempt} - {model}")
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.9,
                    max_tokens=4000
                )
                text = response.choices[0].message.content.strip()

                print("\n--- RAW (500 chars) ---")
                print(text[:500])
                print("-----------------------\n")

                valid = []
                for line in text.split('\n'):
                    line = line.strip()
                    line = re.sub(r'^[\d\.\-\*\#\s]+', '', line)

                    if '>>' not in line:
                        continue

                    parts = line.split('>>')
                    if len(parts) < 3:
                        continue

                    img_prompt = parts[0].strip()
                    vid_prompt = parts[1].strip()
                    sfx_prompt = parts[2].strip()

                    # Validate
                    if len(img_prompt) < 80:
                        print(f"⚠️ Image too short: {len(img_prompt)}")
                        continue

                    if len(vid_prompt) < 10:
                        print(f"⚠️ Video too short")
                        continue

                    if len(sfx_prompt) < 10:
                        print(f"⚠️ SFX too short")
                        continue

                    # Character check
                    char_word = char_looks.split(",")[0].lower()
                    if char_word not in img_prompt.lower():
                        img_prompt = f"{full_char}, {img_prompt}"

                    fixed = (
                        f"{img_prompt} >> "
                        f"{vid_prompt} >> "
                        f"{sfx_prompt}"
                    )
                    valid.append(fixed)
                    print(f"✅ Scene {len(valid)} valid!")

                if len(valid) >= scene_count * 0.7:
                    print(f"✅ {len(valid)} scenes ready!")
                    return valid[:scene_count]
                else:
                    print(f"⚠️ Only {len(valid)}. Retrying...")
                    time.sleep(2)

            except Exception as e:
                print(f"⚠️ Failed: {e}")
                time.sleep(2)

    return None

# ============================================================
# METADATA GENERATOR
# ============================================================
def generate_viral_metadata(video_type, topic, character):
    system = "You are a YouTube viral expert for cartoon comedy channels."

    char_name = character.split("|")[0].strip()

    if video_type == "short":
        format_hint = "YouTube Shorts 9:16"
        title_note  = "Funny Hindi title with emoji, max 60 chars, add #shorts"
    else:
        format_hint = "YouTube Long Video 16:9"
        title_note  = "Funny engaging title, max 70 chars"

    prompt = f"""Topic: '{topic}'
Character: {char_name}
Style: Tom & Jerry cartoon comedy
Format: {format_hint}

Create VIRAL metadata:
TITLE: [{title_note}]
DESC: [2-3 funny lines about cartoon comedy + subscribe CTA]
TAGS: [15 viral cartoon comedy tags]
MUSIC: [funny upbeat cartoon bgm style - 5 words]"""

    models        = get_live_free_models()
    default_music = "funny upbeat Tom Jerry cartoon"

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

            title = re.search(
                r"TITLE:\s*(.*)", text
            ).group(1).strip()

            desc = re.search(
                r"DESC:\s*([\s\S]*?)(?:TAGS:|$)", text
            ).group(1).strip()

            tags = re.search(
                r"TAGS:\s*(.*)", text
            ).group(1).strip()

            music = re.search(
                r"MUSIC:\s*(.*)", text
            )
            music = music.group(1).strip() if music else default_music

            with open(MUSIC_FILE, "w", encoding="utf-8") as f:
                f.write(music)

            print(f"✅ Metadata: {title}")
            return title, desc, tags

        except Exception as e:
            print(f"⚠️ Failed: {e}")
            time.sleep(1)

    with open(MUSIC_FILE, "w", encoding="utf-8") as f:
        f.write(default_music)

    return (
        f"😂 {char_name} Ki Masti! #shorts",
        "Dekhो cartoon ki mazedaar duniya! Subscribe karo! 🔔",
        "cartoon, funny, comedy, shorts, viral, animation"
    )

# ============================================================
# SAVE PROMPTS
# ============================================================
def save_prompts(script_lines, character):
    char_parts = character.split("|")
    char_name  = char_parts[0].strip()
    char_looks = char_parts[1].strip() if len(char_parts) > 1 else ""
    full_char  = f"{char_looks}, named {char_name}"

    validated = []
    for idx, line in enumerate(script_lines, 1):
        if ">>" not in line:
            continue

        parts = line.split(">>")
        if len(parts) < 3:
            continue

        img_prompt = parts[0].strip()
        vid_prompt = parts[1].strip()
        sfx_prompt = parts[2].strip()

        # Character fix
        char_word = char_looks.split(",")[0].lower()
        if char_word not in img_prompt.lower():
            img_prompt = f"{full_char}, {img_prompt}"

        final = f"{img_prompt} >> {vid_prompt} >> {sfx_prompt}"
        validated.append(final)

        print(f"\n✅ Scene {idx}:")
        print(f"   🎨 IMG: {img_prompt[:70]}...")
        print(f"   🎬 VID: {vid_prompt[:50]}...")
        print(f"   🔊 SFX: {sfx_prompt[:50]}...")

    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        for line in validated:
            f.write(line + "\n")

    print(f"\n✅ {len(validated)} scenes saved!")
    return validated

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

    topics  = [t.strip() for t in content.split("\n") if t.strip()]
    current = topics[0]

    print(f"\n{'='*55}")
    print(f"📖 Topic: {current}")
    print(f"{'='*55}\n")

    video_type, duration_sec, topic = parse_story_line(current)
    scene_count  = calculate_scenes(video_type, duration_sec)
    visual_style = detect_visual_style(topic)

    print(f"📺 Type   : {video_type.upper()}")
    print(f"⏱️  Time   : {duration_sec}s")
    print(f"🎬 Scenes : {scene_count}")
    print(f"🎨 Style  : {visual_style}")
    print(f"📝 Topic  : {topic}\n")

    # Character
    print("👤 Creating character...")
    character = generate_character(topic, visual_style)

    # Script
    print("\n🎬 Generating Tom & Jerry script...")
    script_lines = generate_tom_jerry_script(
        video_type, duration_sec,
        topic, character, scene_count
    )

    if not script_lines:
        print("❌ Script failed!")
        sys.exit(1)

    # Save
    print("\n💾 Saving prompts...")
    validated = save_prompts(script_lines, character)

    # Config
    config = {
        "video_type"   : video_type,
        "duration_sec" : duration_sec,
        "topic"        : topic,
        "character"    : character,
        "visual_style" : visual_style,
        "scene_count"  : len(validated),
        "aspect_ratio" : "9:16" if video_type == "short" else "16:9",
        "style"        : "tom_and_jerry"
    }

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # Metadata
    print("\n🚀 Generating metadata...")
    title, desc, tags = generate_viral_metadata(
        video_type, topic, character
    )

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        f.write(f"TITLE: {title}\n")
        f.write(f"DESC: {desc}\n")
        f.write(f"TAGS: {tags}\n")
        f.write(f"VIDEO_TYPE: {video_type}\n")

    print(f"\n{'='*55}")
    print(f"🎉 DONE!")
    print(f"   🎬 Title    : {title}")
    print(f"   👤 Character: {character.split('|')[0].strip()}")
    print(f"   🎨 Scenes   : {len(validated)}")
    print(f"{'='*55}\n")

    # Remove used story
    remaining = topics[1:]
    with open(STORY_FILE, "w", encoding="utf-8") as f:
        f.write(
            "\n".join(remaining) + "\n"
            if remaining else ""
        )

if __name__ == "__main__":
    process_stories()
