import os
import json
from openai import OpenAI

XKIRO_API_KEY = os.getenv("XKIRO_API_KEY")
client = OpenAI(api_key=XKIRO_API_KEY, base_url="https://api.xkiro.com/v1") if XKIRO_API_KEY else None

def main():
    if not client: return
    with open("client_setup.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        
    old_topic = config["topic"]
    print(f"🔄 Generating New Topic (Old was: {old_topic})...")
    
    prompt = f"Give me a NEW, unique 1-sentence story idea for a YouTube short video. It must involve the characters: '{config['character_anchor']}'. It must be different from: '{old_topic}'. Reply ONLY with the new topic sentence."
    
    try:
        response = client.chat.completions.create(
            model="qwen-2.5-72b-instruct", # Fast model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9
        )
        new_topic = response.choices[0].message.content.strip().replace('"', '')
        
        config["topic"] = new_topic
        
        with open("client_setup.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
            
        print(f"✅ Successfully updated client_setup.json with NEW topic: {new_topic}")
    except Exception as e:
        print(f"⚠️ Failed to generate new topic: {e}")

if __name__ == "__main__":
    main()
