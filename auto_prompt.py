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


def generate_ai_script(duration_sec, topic):
    target_scenes = max(2, math.ceil(int(duration_sec) / 5))

    system_prompt = """You are a Master AI Video Prompt Engineer specializing in DIALOGUE-DRIVEN 
DIRECT Text-to-Video generation for tools like Veo, Kling, Sora, Runway, Upsampler (these tools 
take ONE SINGLE FULL TEXT PROMPT and directly generate a 5-second video clip). 
You strictly follow instructions. Output ONLY the raw scene prompts. 
NO tables, NO intro, NO outro, NO explanations, NO markdown formatting."""

    user_prompt = f"""Task: Create a COMPLETE, highly engaging, DIALOGUE-BASED video story for: "{topic}".
Total Duration: {duration_sec} seconds. Generate EXACTLY {target_scenes} scenes.
Each scene = ONE complete, ready-to-use, single-paragraph prompt for a 5-SECOND AI video clip.

🚨 CRITICAL RULE - EVERYTHING IN ONE FLOWING PARAGRAPH (NO SYMBOLS):
- Each scene prompt must be written as ONE natural, flowing, detailed paragraph that includes:
  1) Full character physical description (repeated every time for consistency)
  2) Full background/location description (repeated every time)
  3) Camera angle and camera movement for this shot
  4) The action happening in the scene
  5) The spoken dialogue (who says what, in quotes)
  6) The sound effects
  7) Background music status (on/off and mood)

🚨 CHARACTER CONSISTENCY:
- Invent SPECIFIC characters with FULL fixed description: name, face, hair, skin tone, exact clothing/colors.
- REPEAT the COMPLETE character description in EVERY scene (video AI has no memory).

🚨 BACKGROUND CONSISTENCY:
- Invent ONE specific detailed location.
- REPEAT this FULL background in every scene.

🚨 CAMERA (Mandatory, varies each scene):
- Describe camera instruction: "close-up zoom", "wide drone shot", "tracking shot", "low-angle", "slow-motion", etc.
- VARY the camera angle every scene for cinematic feel.

🚨 DIALOGUE (Mandatory in every scene):
- ONE short dialogue line per scene by a NAMED character (max 10-14 words for 5 seconds).
- Use natural Hindi/Hinglish/English matching the story mood.

🚨 AUDIO (Mandatory):
- Mention sound effects clearly.
- Mention if background music plays or not (and its mood if yes).

🚨 STORY ARC:
- Scene 1 = Strong HOOK (striking visual + punchy dialogue).
- Middle = Rising action with dialogue.
- Last = Clear RESOLUTION with meaningful closing dialogue.

🚨 YOUTUBE SAFE: NO blood, NO weapons, NO gore. Family-Friendly only.

🚨 OUTPUT FORMAT:
- Write each scene as ONE single continuous paragraph.
- After EACH scene, add a line with ONLY: ###
- Do NOT number scenes. Just paragraph, then ###, then next paragraph.

EXAMPLE:
Meera, a young Indian girl with a tight black ponytail, sharp eyes, light brown skin, wearing an orange racing jacket with tiger-stripe patches, sits inside her orange Tiger-liveried race car with tiger stripe decals, parked on a dusty golden-brown countryside race track with rocky mountains and a wooden bridge in the background under bright afternoon sun, the camera slowly zooms into a close-up of her determined face as she grips the steering wheel, Meera says with fierce confidence, "मेरी टाइगर कार स्पीड के लिए रेडी है!", the loud sound of her engine revving can be heard, there is no background music, only clear dialogue and engine sound.
###

START YOUR RESPONSE DIRECTLY WITH THE FIRST SCENE:"""

    models = get_live_free_models()
    attempt = 1
    max_attempts = 10

    for model_name in models:
        for _ in range(2):
            if attempt > max_attempts:
                print("❌ ERROR: 10 attempts ho gaye par kisi AI ne sahi format nahi diya. Exiting.")
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
                    print("\n--- RAW AI OUTPUT ---")
                    print(text)
                    print("---------------------\n")

                    raw_scenes = text.split("###")
                    valid_scenes = []
                    for scene in raw_scenes:
                        scene = scene.strip()
                        scene = re.sub(r'^[\d\.\-\*\s]+', '', scene)
                        scene = re.sub(r'^(Scene\s*\d+\s*[:\-]?\s*)', '', scene, flags=re.IGNORECASE)
                        if len(scene) > 30:
                            valid_scenes.append(scene)

                    if len(valid_scenes) > 0:
                        print(f"✅ Success! {len(valid_scenes)} valid scenes from {model_name}.")
                        return "\n\n".join(valid_scenes[:target_scenes])
                    else:
                        print(f"⚠️ AI ne script di, par format galat tha. Retrying...")
            except Exception as e:
                print(f"⚠️ Model {model_name} failed: {e}. Switching...")
                time.sleep(2)

            attempt += 1

    return None


def generate_ai_metadata(topic):
    system_prompt = """You are a Top-Tier YouTube Shorts Growth Hacker & Viral Content Strategist.
You have analyzed THOUSANDS of viral Shorts (10M+ views). You know proven patterns, hook-words, 
curiosity-gaps, emoji placement, hashtag strategy for Algorithm."""

    user_prompt = f"""Topic: "{topic}"

Create VIRAL YouTube Shorts metadata using proven patterns from top viral videos.

RULES:
- TITLE: Max 70 chars. Include curiosity hook/emotional trigger/power word. Add 1-2 emojis.
- DESC: 2-3 lines. First line hooks curiosity. Include call-to-action. End with 4-6 hashtags 
  (mix broad like #shorts #viral #fyp + niche related to topic).
- TAGS: 12-15 comma separated. Mix broad viral tags + niche genre tags + topic-specific keywords.
- MUSIC: 5-8 word mood description matching story emotion.

FORMAT:
TITLE: [title]
DESC: [description with hashtags]
TAGS: [tag1, tag2, ...]
MUSIC: [music prompt]"""

    models = get_live_free_models()
    music_prompt = "dark emotional cinematic background score"

    for model_name in models[:3]:
        try:
            print(f"🎵 Generating Metadata using {model_name}...")
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.9
            )
            text = response.choices[0].message.content

            title_match = re.search(r"TITLE:\s*(.*)", text)
            desc_match = re.search(r"DESC:\s*([\s\S]*?)(?:TAGS:|$)", text)
            tags_match = re.search(r"TAGS:\s*([\s\S]*?)(?:MUSIC:|$)", text)
            music_match = re.search(r"MUSIC:\s*(.*)", text)

            if not (title_match and desc_match and tags_match):
                print(f"⚠️ {model_name} ne format sahi nahi diya...")
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
            print(f"📌 DESC: {desc}")
            print(f"📌 TAGS: {tags}")
            return title, desc, tags
        except Exception as e:
            print(f"⚠️ Model failed: {e}")
            time.sleep(1)

    with open("music_prompt.txt", "w", encoding="utf-8") as f:
        f.write(music_prompt)
    fallback_title = f"You Won't Believe What Happens 😱 | {topic[:40]}"
    fallback_desc = f"This {topic} story will shock you 💔 Watch till end!\n#shorts #viral #fyp #trending"
    fallback_tags = f"shorts, viral shorts, trending, fyp, {topic.lower()}"
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
    parts = topics[0].split("|")
    duration_sec, topic = (int(re.search(r'\d+', parts[0]).group()), parts[1].strip()) if len(parts) > 1 else (30, topics[0])

    print(f"📝 Topic: {topic}, Duration: {duration_sec}s")

    ai_output = generate_ai_script(duration_sec, topic)

    if not ai_output:
        print("❌ CRITICAL ERROR: AI failed after 10 attempts.")
        sys.exit(1)

    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        f.write(ai_output + "\n")

    title, desc, tags = generate_ai_metadata(topic)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        f.write(f"TITLE: {title}\nDESC: {desc}\nTAGS: {tags}")
    
    with open(STORY_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(topics[1:]) + "\n" if len(topics) > 1 else "")
    
    print("🚀 All processes completed successfully!")


if __name__ == "__main__":
    process_stories()
