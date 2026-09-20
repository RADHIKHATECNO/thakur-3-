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
        "scary", "darr", "raat", "shaitan",
        "zombie", "vampire", "haunted"
    ]):
        return "2D Anime dark cinematic style"

    # Realistic Human / Comedy Human
    if any(w in topic_lower for w in [
        "human", "insaan", "aadmi", "ladka",
        "ladki", "realistic", "real", "banda",
        "uncle", "aunty", "bhai", "dost"
    ]):
        return "Pixar 3D animation style"

    # Animal
    if any(w in topic_lower for w in [
        "animal", "janwar", "dog", "cat",
        "kutta", "billi", "tiger", "lion",
        "elephant", "hathi", "monkey", "bandar"
    ]):
        return "cute funny cartoon animal style"

    # Robot/Sci-fi
    if any(w in topic_lower for w in [
        "robot", "sci-fi", "future", "space",
        "alien", "machine", "cyber", "android"
    ]):
        return "futuristic 3D CGI cinematic style"

    # Vehicle/Car
    if any(w in topic_lower for w in [
        "car", "gaadi", "truck", "bus",
        "train", "bike", "vehicle", "auto"
    ]):
        return "Pixar 3D funny cartoon style"

    # Default
    return "Pixar 3D funny cartoon style"

# ============================================================
# CHARACTER GENERATOR
# ============================================================
def generate_character(topic, visual_style):
    """
    Topic se ek detailed consistent character banao
    Jo poori video mein EXACTLY same rahe
    """
    system = (
        "You are a creative character designer for animated movies. "
        "Create ONE very detailed character description. "
        "Be extremely specific about every visual detail."
    )

    prompt = f"""Topic: '{topic}'
Visual Style: {visual_style}

Create ONE unique main character with EXTREMELY detailed appearance.

Include ALL of these:
1. Exact funny Hindi name
2. Body type (fat/thin/tall/short)
3. Skin color
4. Hair (color, style, length)
5. Eyes (color, size, expression)
6. Clothing (exact colors, patterns, style)
7. Accessories (glasses, hat, jewelry etc)
8. One signature funny prop or feature
9. Default facial expression
10. One funny personality trait

Format EXACTLY like this:
NAME | [full appearance in English - all details] | [funny trait]

Example:
Motu Singh | fat funny indian woman, wheatish skin, black hair tied in bun with red flowers, big round googly eyes, chubby red cheeks, wearing bright orange saree with golden border and green blouse, red bindi on forehead, gold bangles on both wrists, always carrying a tiffin box, default angry-but-funny expression | always stuck in traffic and argues with everyone

ONE LINE ONLY - Be very detailed:"""

    models = get_live_free_models()
    for model in models[:4]:
        try:
            print(f"👤 Character generation - Model: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9
            )
            char = response.choices[0].message.content.strip()

            # Pehli line lo
            char = char.split('\n')[0].strip()
            char = re.sub(r'^[\d\.\-\*\s]+', '', char)

            # Validate - minimum 3 parts aur detailed honi chahiye
            if '|' in char and len(char) > 100:
                print(f"✅ Character Created!")
                print(f"   {char[:100]}...")
                return char
            else:
                print(f"⚠️ Character too short, retrying...")

        except Exception as e:
            print(f"⚠️ Model {model} failed: {e}")
            time.sleep(1)

    # Detailed Fallback character
    return (
        "Raju Sharma | small chubby funny indian man, "
        "wheatish skin, black messy hair always uncombed, "
        "big surprised round eyes, thick black mustache, "
        "wearing bright yellow kurta with white pajama, "
        "red rubber slippers, always holding a chai cup, "
        "default shocked expression with open mouth | "
        "always does everything wrong but thinks he is genius"
    )

# ============================================================
# FULL SCRIPT GENERATOR
# ============================================================
def generate_full_script(
    video_type, duration_sec, topic,
    character, scene_count
):
    """
    Har scene ke liye 3 parts banao:
    NARRATION >> IMAGE_PROMPT >> VIDEO_PROMPT
    """

    # Character parts nikalo
    char_parts = character.split("|")
    char_name  = char_parts[0].strip() if len(char_parts) > 0 else "Raju"
    char_looks = char_parts[1].strip() if len(char_parts) > 1 else "funny cartoon man"
    char_trait = char_parts[2].strip() if len(char_parts) > 2 else "always funny"

    visual_style = detect_visual_style(topic)

    # Aspect ratio
    if video_type == "short":
        aspect      = "vertical 9:16 composition"
        image_style = f"{visual_style}, {aspect}"
    else:
        aspect      = "horizontal 16:9 widescreen"
        image_style = f"{visual_style}, {aspect}"

    # Full character description for image prompt
    full_char_desc = (
        f"{visual_style}, "
        f"{char_looks}, "
        f"named {char_name}"
    )

    system = """You are a master Hindi storyteller and YouTube expert.
You create PERFECTLY formatted scripts.
Output ONLY scene lines. No extra text. No numbering. No explanation."""

    prompt = f"""Topic: '{topic}'
Character: {char_name}
Full Character Appearance: {char_looks}
Character Trait: {char_trait}
Visual Style: {visual_style}
Aspect Ratio: {aspect}
Total Scenes: {scene_count}
Mood: 100% FUNNY, HAPPY, ENERGETIC - Zero horror, zero sadness

🎯 YOUR JOB: Create EXACTLY {scene_count} scenes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 FORMAT (use >> to separate):
[Hindi narration] >> [Full image prompt] >> [Video + SFX prompt]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 HINDI NARRATION RULES:
- Energetic, funny, use "अरे!", "वाह!", "ओहो!", "हाहा!"
- Exactly describe what is happening on screen
- Max 20 words per scene
- Pure Hindi only

🔴 IMAGE PROMPT RULES (CRITICAL):
- ALWAYS start with: "{full_char_desc}"
- Then add: [EXACT ACTION in this scene]
- Then add: [BACKGROUND details]
- Then add: {aspect}, bright vivid colors, expressive funny face, high quality render, no text, no watermark
- MINIMUM 80 words
- NEVER shorten character description

🔴 VIDEO PROMPT RULES:
- Camera movement (zoom/pan/shake)
- Sound effects (SFX only)
- End with: no bgm, no voice
- Max 30 words

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 PERFECT EXAMPLE:
अरे! {char_name} ट्रैफिक में फंस गई! >> {visual_style}, {char_looks}, named {char_name}, stuck in massive traffic jam with hundreds of colorful cars honking, both hands pressing horn on steering wheel, steam coming from ears, angry red face, busy indian street background with shops and signs, {aspect}, bright vivid colors, expressive funny face, high quality render, no text, no watermark >> Fast zoom in on angry face, camera shake, SFX: loud traffic horns, engine rumbles, city crowd noise, no bgm, no voice
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎬 STORY STRUCTURE:
- Scene 1: SUPER HOOK - most shocking/funny moment
- Scenes 2 to {scene_count-1}: Story action/comedy
- Scene {scene_count}: Happy ending/resolution

START DIRECTLY WITH SCENE 1 (no intro text):"""

    models    = get_live_free_models()
    max_tries = 10

    for attempt, model in enumerate(models, 1):
        if attempt > max_tries:
            break
        for retry in range(2):
            print(f"🔄 Script Attempt {attempt} - Model: {model}")
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.85,
                    max_tokens=4000
                )
                text = response.choices[0].message.content.strip()

                print("\n--- RAW OUTPUT (first 600 chars) ---")
                print(text[:600])
                print("-------------------------------------\n")

                # Valid lines filter
                valid = []
                for line in text.split('\n'):
                    line = line.strip()

                    # Clean karo
                    line = re.sub(r'^[\d\.\-\*\#\s]+', '', line)

                    if '>>' not in line:
                        continue

                    parts = line.split('>>')
                    if len(parts) < 3:
                        continue

                    narration  = parts[0].strip()
                    img_prompt = parts[1].strip()
                    vid_prompt = parts[2].strip()

                    # Validations
                    if len(narration) < 5:
                        print(f"⚠️ Narration too short: {narration}")
                        continue

                    if len(img_prompt) < 80:
                        print(f"⚠️ Image prompt too short ({len(img_prompt)} chars): {img_prompt[:50]}")
                        continue

                    if len(vid_prompt) < 10:
                        print(f"⚠️ Video prompt too short")
                        continue

                    # Character consistency check
                    char_first_word = char_looks.split(",")[0].strip().lower()
                    if char_first_word not in img_prompt.lower():
                        print(f"⚠️ Character missing from image prompt! Adding...")
                        # Auto fix - character add karo
                        img_prompt = (
                            f"{full_char_desc}, "
                            f"{img_prompt}"
                        )

                    # Reconstruct line
                    fixed_line = (
                        f"{narration} >> "
                        f"{img_prompt} >> "
                        f"{vid_prompt}"
                    )
                    valid.append(fixed_line)
                    print(f"✅ Scene {len(valid)} valid!")

                if len(valid) >= scene_count * 0.7:
                    print(f"\n✅ {len(valid)} valid scenes generated!")
                    return valid[:scene_count]
                else:
                    print(f"⚠️ Only {len(valid)}/{scene_count} valid. Retrying...")
                    time.sleep(2)

            except Exception as e:
                print(f"⚠️ Model {model} failed: {e}")
                time.sleep(2)

    return None

# ============================================================
# METADATA GENERATOR
# ============================================================
def generate_viral_metadata(video_type, topic, character):
    system = (
        "You are a YouTube viral growth expert. "
        "Create metadata that gets maximum clicks."
    )

    char_name = character.split("|")[0].strip()

    if video_type == "short":
        format_hint = "YouTube Shorts 9:16 vertical"
        title_note  = "Short punchy Hindi title with emoji, max 60 chars, add #shorts"
    else:
        format_hint = "YouTube Long Video 16:9 horizontal"
        title_note  = "Engaging Hindi title with keywords, max 70 chars"

    prompt = f"""Topic: '{topic}'
Main Character: {char_name}
Format: {format_hint}
Mood: Funny, Happy, Family-Friendly, Comedy

Create VIRAL YouTube metadata:

TITLE: [{title_note}]
DESC: [3 funny engaging lines in Hindi + subscribe CTA]
TAGS: [15 viral Hindi comedy tags comma separated]
MUSIC: [5-7 word upbeat funny background music style]"""

    models        = get_live_free_models()
    default_music = "upbeat funny cartoon comedy background music"

    for model in models[:5]:
        try:
            print(f"📊 Metadata - Model: {model}")
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

            music_match = re.search(r"MUSIC:\s*(.*)", text)
            music = music_match.group(1).strip() if music_match else default_music

            with open(MUSIC_FILE, "w", encoding="utf-8") as f:
                f.write(music)

            print(f"✅ Metadata generated!")
            print(f"   Title: {title}")
            return title, desc, tags

        except Exception as e:
            print(f"⚠️ Metadata model {model} failed: {e}")
            time.sleep(1)

    # Fallback
    with open(MUSIC_FILE, "w", encoding="utf-8") as f:
        f.write(default_music)

    return (
        f"😂 {topic[:40]} - Funny Story! #shorts",
        "Ek mazedaar kahani! Subscribe karo! 🔔",
        "funny, comedy, hindi, shorts, viral, trending"
    )

# ============================================================
# PROMPTS SAVER + VALIDATOR
# ============================================================
def save_and_validate_prompts(script_lines, character):
    """
    prompts.txt save karo aur validate karo
    """
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

        narration  = parts[0].strip()
        img_prompt = parts[1].strip()
        vid_prompt = parts[2].strip()

        # Final character consistency fix
        char_first = char_looks.split(",")[0].strip().lower()
        if char_first not in img_prompt.lower():
            img_prompt = f"{full_char}, {img_prompt}"

        final_line = f"{narration} >> {img_prompt} >> {vid_prompt}"
        validated.append(final_line)

        print(f"\n✅ Scene {idx}:")
        print(f"   🎙️  NAR: {narration[:60]}...")
        print(f"   🎨 IMG: {img_prompt[:80]}...")
        print(f"   🎬 VID: {vid_prompt[:50]}...")

    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        for line in validated:
            f.write(line + "\n")

    print(f"\n✅ {len(validated)} scenes saved to prompts.txt!")
    return validated

# ============================================================
# MAIN
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

    topics  = [t.strip() for t in content.split("\n") if t.strip()]
    current = topics[0]

    print(f"\n{'='*55}")
    print(f"📖 Processing: {current}")
    print(f"{'='*55}\n")

    # Parse
    video_type, duration_sec, topic = parse_story_line(current)
    scene_count  = calculate_scenes(video_type, duration_sec)
    visual_style = detect_visual_style(topic)

    print(f"📺 Type         : {video_type.upper()}")
    print(f"⏱️  Duration     : {duration_sec}s")
    print(f"🎬 Scenes       : {scene_count}")
    print(f"🎨 Visual Style : {visual_style}")
    print(f"📝 Topic        : {topic}\n")

    # Step 1: Character banao
    print("👤 Creating detailed character...")
    character = generate_character(topic, visual_style)
    print(f"\n✅ Character: {character[:120]}...\n")

    # Step 2: Full script banao
    print("📝 Generating full script...")
    script_lines = generate_full_script(
        video_type, duration_sec,
        topic, character, scene_count
    )

    if not script_lines:
        print("❌ Script generation failed after all attempts!")
        sys.exit(1)

    # Step 3: Save + validate
    print("\n💾 Saving and validating prompts...")
    validated = save_and_validate_prompts(script_lines, character)

    # Step 4: Config save
    config = {
        "video_type"   : video_type,
        "duration_sec" : duration_sec,
        "topic"        : topic,
        "character"    : character,
        "visual_style" : visual_style,
        "scene_count"  : len(validated),
        "aspect_ratio" : "9:16" if video_type == "short" else "16:9"
    }

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✅ Config saved!")

    # Step 5: Metadata
    print("\n🚀 Generating viral metadata...")
    title, desc, tags = generate_viral_metadata(
        video_type, topic, character
    )

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        f.write(f"TITLE: {title}\n")
        f.write(f"DESC: {desc}\n")
        f.write(f"TAGS: {tags}\n")
        f.write(f"VIDEO_TYPE: {video_type}\n")

    # Summary
    print(f"\n{'='*55}")
    print(f"🎉 STAGE 1 COMPLETE!")
    print(f"   📺 Title     : {title}")
    print(f"   👤 Character : {character.split('|')[0].strip()}")
    print(f"   🎬 Scenes    : {len(validated)}")
    print(f"   🎨 Style     : {visual_style}")
    print(f"{'='*55}\n")

    # Used story hatao
    remaining = topics[1:]
    with open(STORY_FILE, "w", encoding="utf-8") as f:
        f.write(
            "\n".join(remaining) + "\n"
            if remaining else ""
        )

    print("🚀 Pipeline Stage 1 Complete!")

if __name__ == "__main__":
    process_stories()
