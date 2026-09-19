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
        models_list = [m["id"] for m in data.get("data", []) if m.get("pricing", {}).get("prompt") == "0" and m.get("pricing", {}).get("completion") == "0"]
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


def generate_ai_script(duration_sec, topic, story_type, mood):
    target_scenes = max(2, math.ceil(int(duration_sec) / 5))
    
    # 🔴 Mood-based lighting/tone guidance
    mood_map = {
        "sad": "gloomy lighting, tears, slow emotional movements, melancholic atmosphere",
        "happy": "bright sunny lighting, smiling faces, cheerful energy, vibrant colors",
        "horror": "dark shadowy lighting, nervous expressions, eerie atmosphere, suspenseful tension",
        "interesting": "dynamic lighting, curious expressions, fast-paced engaging action",
        "romantic": "warm golden hour lighting, loving gazes, soft intimate atmosphere",
        "motivational": "inspiring bright lighting, determined expressions, uplifting energy",
        "thriller": "dramatic high-contrast lighting, intense expressions, edge-of-seat tension"
    }
    mood_desc = mood_map.get(mood.lower(), "cinematic dramatic lighting, expressive emotions")

    # 🔴 Character type guidance
    char_map = {
        "anime": "Japanese anime-style animated characters with large expressive eyes, colorful hair, detailed anime art style",
        "human": "realistic photorealistic human characters with natural skin texture, real human proportions",
        "cartoon": "Western cartoon-style animated characters with exaggerated features, bold outlines",
        "realistic": "ultra-realistic human characters, lifelike details, natural lighting",
        "sci-fi": "futuristic sci-fi characters with cybernetic enhancements, neon accents, high-tech clothing"
    }
    char_desc = char_map.get(story_type.lower(), "cinematic realistic characters")

    system_prompt = """You are a Master Storytelling Director specializing in creating COMPLETE, 
EMOTIONALLY ENGAGING, DIALOGUE-DRIVEN video stories for Direct Text-to-Video AI tools (Veo, Kling, 
Sora, Runway, Upsampler). You create stories with proper BEGINNING → MIDDLE → END structure like 
a real movie/series episode. You strictly follow instructions. Output ONLY raw scene prompts. 
NO tables, NO numbering, NO intro/outro text."""

    user_prompt = f"""Create a COMPLETE {mood.upper()} story with {story_type.upper()} characters based on: "{topic}".

📊 SPECIFICATIONS:
- Total Duration: {duration_sec} seconds ({target_scenes} scenes × 5 seconds each)
- Character Style: {char_desc}
- Mood/Tone: {mood_desc}

🎬 STORY STRUCTURE (CRITICAL):
- Scenes 1-2 (First 10 seconds): POWERFUL HOOK - Start with the most dramatic/emotional/shocking 
  moment that immediately grabs attention. Make viewers NEED to watch till the end.
- Scenes 3 to {target_scenes-3}: RISING ACTION - Build the story with connected narrative flow. 
  Each scene must naturally lead to the next. Show conflict, struggle, tension building.
- Last 2-3 scenes: CLIMAX + RESOLUTION - The big emotional payoff. Clear ending with closure or 
  powerful message that satisfies the viewer.

🚨 DIALOGUE RULES (CRITICAL):
- EVERY scene MUST have ONE dialogue line spoken by a named character.
- Dialogue length: 20-30 WORDS (10-12 seconds when spoken naturally) - DOUBLE the previous limit!
- Dialogue must be EMOTIONAL, NATURAL, and ADVANCE THE STORY forward.
- Use {mood} mood-appropriate language (sad=emotional/crying tone, happy=excited/cheerful, etc.)
- Language: Natural Hindi/Hinglish mix (use English words where natural, Hindi for emotions)

🎭 CHARACTER CONSISTENCY (CRITICAL):
- Invent 1-3 SPECIFIC main characters with FULL detailed description:
  * Character Type: {char_desc}
  * Name, age, gender
  * Face: eye color, facial features, expression style
  * Hair: color, style, length
  * Clothing: exact colors, style, accessories
  * Unique trait: scar/glasses/necklace/tattoo (for AI to remember)
- REPEAT THE EXACT SAME FULL CHARACTER DESCRIPTION word-for-word in EVERY scene 
  (the video AI has ZERO memory between scenes - if you change even one word, the character face will change!)

🌍 BACKGROUND CONSISTENCY (CRITICAL):
- Invent ONE main location/setting with FULL details:
  * Type of place, architecture style
  * Colors, lighting, weather, time of day
  * Key landmarks/objects visible in background
- REPEAT THE EXACT SAME FULL BACKGROUND DESCRIPTION in every scene (only camera angle changes)

📹 CAMERA WORK (CRITICAL - Must vary each scene):
- Scene 1-2 (Hook): Use dramatic camera angles (low-angle hero shot, extreme close-up on shocked face, etc.)
- Every scene must specify ONE camera instruction:
  "close-up slow zoom into face", "wide establishing shot", "tracking shot following character", 
  "over-the-shoulder shot", "low-angle dramatic shot", "high-angle bird's eye view", 
  "slow-motion shot", "handheld shaky cam", "smooth dolly shot", "pan left to reveal", etc.
- VARY camera angle every scene for cinematic professional feel

🔊 AUDIO CLARITY (CRITICAL):
- After dialogue, clearly specify:
  * SFX: Specific sound effects matching the action (footsteps, door slam, wind, crying, etc.)
  * BGM: Either "No background music, dialogue focus" OR "Soft [mood] background music, low volume"
- Use "No BGM" for heavy dialogue scenes, light BGM only for action/transition scenes

🎨 MOOD INTEGRATION:
- {mood.upper()} mood must reflect in:
  * Lighting: {mood_desc}
  * Character expressions and body language
  * Dialogue tone and word choice
  * Sound effects selection

📝 OUTPUT FORMAT (VERY IMPORTANT):
- Write each scene as ONE single flowing detailed paragraph (like a movie script scene description)
- Include everything in natural descriptive sentences: character details, background, camera, action, 
  dialogue (in quotes with character name), sound effects, music status
- After each scene paragraph, add a line with ONLY: ###
- NO scene numbers, NO titles, just paragraph → ### → next paragraph

EXAMPLE (for anime sad story):
Akira, a 17-year-old Japanese anime boy with spiky silver hair, bright blue eyes filled with tears, wearing a black high school uniform with a red scarf, standing alone on an empty rainy rooftop of a tall grey concrete school building under dark stormy clouds at sunset, the camera does a slow close-up zoom into his devastated crying face as rain pours down, Akira says with a breaking voice while crying, "Tumne kaha tha ki tum hamesha mere saath rahoge, phir kyun chale gaye? Main akela kaise jee paunga is duniya mein bina tumhare? Mere best friend, please wapas aa jao!", the sound of heavy rain hitting the rooftop and distant thunder rumbling can be heard, no background music, only dialogue and rain sound effects.
###

NOW CREATE THE FULL {target_scenes}-SCENE STORY. START DIRECTLY WITH SCENE 1:"""

    models = get_live_free_models()
    attempt = 1
    max_attempts = 10

    for model_name in models:
        for _ in range(2):
            if attempt > max_attempts:
                print("❌ ERROR: 10 attempts failed. Exiting.")
                return None

            print(f"🔄 Attempt {attempt}/{max_attempts} - Model: {model_name}...")
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.85,
                    max_tokens=8000  # Increased for longer stories
                )
                text = response.choices[0].message.content

                if text:
                    print("\n--- RAW AI OUTPUT (First 500 chars) ---")
                    print(text[:500] + "...")
                    print("----------------------------------------\n")

                    raw_scenes = text.split("###")
                    valid_scenes = []
                    
                    for scene in raw_scenes:
                        scene = scene.strip()
                        # Remove accidental numbering/titles
                        scene = re.sub(r'^[\d\.\-\*\s]+', '', scene)
                        scene = re.sub(r'^(Scene\s*\d+\s*[:\-]?\s*)', '', scene, flags=re.IGNORECASE)
                        # Must be substantial paragraph
                        if len(scene) > 50:
                            valid_scenes.append(scene)

                    if len(valid_scenes) >= 2:  # At least hook scenes
                        print(f"✅ Success! {len(valid_scenes)} valid scenes from {model_name}.")
                        # Take exact number needed
                        final_scenes = valid_scenes[:target_scenes]
                        return "\n\n".join(final_scenes)
                    else:
                        print(f"⚠️ Only {len(valid_scenes)} scenes found. Retrying...")
                        
            except Exception as e:
                print(f"⚠️ Model {model_name} error: {e}")
                time.sleep(2)

            attempt += 1

    return None


def generate_ai_metadata(topic, mood, duration_sec):
    system_prompt = """You are a YouTube Algorithm Expert who has studied millions of viral long-form 
YouTube videos (NOT Shorts). You know exactly what titles, descriptions, tags make videos rank high 
in search and recommendations for 3-15 minute story/entertainment videos."""

    user_prompt = f"""Topic: "{topic}"
Mood: {mood}
Duration: {int(duration_sec/60)} minutes

Create VIRAL YouTube metadata for a LONG-FORM video (NOT a Short) using proven patterns.

RULES:
- TITLE: Max 70 chars. Emotional hook + curiosity gap. Add 1-2 emojis. 
  (e.g., "This Will Make You Cry 😭", "The Most Shocking Story Ever Told 😱", 
  "You Won't Believe How This Ends 🔥")
- DESC: 3-5 lines. First line = strong hook. Include story teaser. Add call-to-action 
  ("Subscribe for more stories"). End with 5-8 hashtags mixing:
  * Broad: #story #emotional #viral #trending #youtube
  * Mood-specific: #sadstory #horrortale #inspirational (based on {mood})
  * Topic-specific keywords from the story
- TAGS: 15-20 comma-separated tags for long videos:
  * Broad viral: viral video, trending story, emotional video, must watch
  * Genre: {mood} story, {mood} video, storytelling, narrative
  * Topic-specific keywords
- MUSIC: 5-8 word mood description matching {mood} emotion

FORMAT:
TITLE: [title]
DESC: [description with hashtags]
TAGS: [tag1, tag2, ...]
MUSIC: [music prompt]"""

    models = get_live_free_models()
    music_prompt = f"{mood} emotional cinematic background score"

    for model_name in models[:3]:
        try:
            print(f"🎵 Generating Metadata using {model_name}...")
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.9
            )
            text = response.choices[0].message.content

            title_match = re.search(r"TITLE:\s*(.*)", text)
            desc_match = re.search(r"DESC:\s*([\s\S]*?)(?:TAGS:|$)", text)
            tags_match = re.search(r"TAGS:\s*([\s\S]*?)(?:MUSIC:|$)", text)
            music_match = re.search(r"MUSIC:\s*(.*)", text)

            if not (title_match and desc_match and tags_match):
                print(f"⚠️ {model_name} format error...")
                continue

            title = title_match.group(1).strip()
            desc = desc_match.group(1).strip()
            tags = tags_match.group(1).strip()
            if music_match:
                music_prompt = music_match.group(1).strip()

            with open("music_prompt.txt", "w", encoding="utf-8") as f:
                f.write(music_prompt)

            print("✅ Metadata generated!")
            print(f"📌 TITLE: {title}")
            print(f"📌 TAGS: {tags[:100]}...")
            return title, desc, tags
            
        except Exception as e:
            print(f"⚠️ {model_name} failed: {e}")
            time.sleep(1)

    # Fallback
    with open("music_prompt.txt", "w", encoding="utf-8") as f:
        f.write(music_prompt)
    
    fallback_title = f"This {mood.title()} Story Will Touch Your Heart 😭💔"
    fallback_desc = f"Watch this incredible {mood} story till the end. You won't regret it! 🎬\n\n#story #{mood}story #viral #emotional #trending #storytelling #youtube"
    fallback_tags = f"story, {mood} story, emotional story, viral video, trending, storytelling, {topic}, youtube stories"
    return fallback_title, fallback_desc, fallback_tags


def process_stories():
    if not os.path.exists(STORY_FILE):
        print(f"❌ ERROR: {STORY_FILE} not found!")
        sys.exit(1)

    with open(STORY_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        print(f"❌ ERROR: {STORY_FILE} is empty!")
        sys.exit(1)

    topics = [t.strip() for t in content.split("\n") if t.strip()]
    
    # Parse first story line: [type] | [duration] | [mood] | [topic]
    parts = topics[0].split("|")
    
    if len(parts) >= 4:
        story_type = parts[0].strip()
        duration_str = parts[1].strip()
        mood = parts[2].strip()
        topic = parts[3].strip()
        
        # Parse duration (support "5 min", "300 sec", "3 minutes", etc.)
        duration_match = re.search(r'(\d+)\s*(min|sec|minute|second)', duration_str, re.IGNORECASE)
        if duration_match:
            num = int(duration_match.group(1))
            unit = duration_match.group(2).lower()
            if 'min' in unit:
                duration_sec = num * 60
            else:
                duration_sec = num
        else:
            duration_sec = 180  # Default 3 min
            
    else:
        # Old format fallback
        duration_sec = 180
        topic = topics[0]
        story_type = "human"
        mood = "interesting"

    print(f"📝 Story Type: {story_type}")
    print(f"⏱️  Duration: {duration_sec} seconds ({duration_sec/60:.1f} minutes)")
    print(f"🎭 Mood: {mood}")
    print(f"📖 Topic: {topic}")

    ai_output = generate_ai_script(duration_sec, topic, story_type, mood)

    if not ai_output:
        print("❌ CRITICAL: AI failed after 10 attempts.")
        sys.exit(1)

    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        f.write(ai_output + "\n")

    title, desc, tags = generate_ai_metadata(topic, mood, duration_sec)
    
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        f.write(f"TITLE: {title}\nDESC: {desc}\nTAGS: {tags}")

    # Remove first story from queue
    with open(STORY_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(topics[1:]) + "\n" if len(topics) > 1 else "")

    print("🚀 Script generation completed successfully!")


if __name__ == "__main__":
    process_stories()
