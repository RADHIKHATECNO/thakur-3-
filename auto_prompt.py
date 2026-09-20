import os
import re
import random
from openai import OpenAI

# --- Configuration ---
STORY_FILE = "story.txt"
PROMPT_FILE = "prompts.txt"
VOICE_SCRIPT_FILE = "voice_script.txt"
API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    print("❌ Error: OPENROUTER_API_KEY missing!")
    exit()

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

def get_best_free_model():
    # Fallback free models list
    return [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.0-flash-lite-preview-02-05:free",
        "mistralai/mistral-7b-instruct:free"
    ]

def generate_script():
    if not os.path.exists(STORY_FILE):
        print("❌ Error: story.txt missing!")
        return False

    with open(STORY_FILE, "r", encoding="utf-8") as f:
        topic = f.read().strip()

    # Prompting logic with Loop/Hook constraints
    prompt = f"""
    Create a comedy story about: '{topic}'.
    RULES:
    1. NO Horror, NO Fear, NO Weapons. ONLY Comedy/Happiness.
    2. Total Duration: 60 seconds.
    3. HOOK: First 3 seconds must be a shocking question.
    4. LOOP: The LAST sentence must connect smoothly to the FIRST sentence.
    5. Character: Keep ONE consistent character (e.g., 'Raju') throughout.
    6. Format: Line 1 is VISUAL description | Line 2 is NARRATION text.
    7. Narration Text should be in Hinglish (Hindi+English).

    EXAMPLE START:
    VISUAL: A car looking shocked | NARRATION: "क्या आप जानते हैं कार भी बोल सकती है?"
    
    Now generate the full story:
    """

    model = random.choice(get_best_free_model())
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        text = response.choices[0].message.content
        
        with open(PROMPT_FILE, "w", encoding="utf-8") as f:
            f.write(text)
        
        # Extract narration for voice
        voice_lines = []
        for line in text.split('\n'):
            if '|' in line:
                voice_lines.append(line.split('|')[1].strip())
        
        with open(VOICE_SCRIPT_FILE, "w", encoding="utf-8") as f:
            f.write(" ".join(voice_lines))

        print("✅ Script & Voice Script Generated!")
        return True
    except Exception as e:
        print(f"❌ Script Generation Failed: {e}")
        return False

if __name__ == "__main__":
    generate_script()
