import os
import json
import time
from openai import OpenAI

XKIRO_API_KEY = os.getenv("XKIRO_API_KEY")
client = OpenAI(api_key=XKIRO_API_KEY, base_url="https://api.xkiro.com/v1") if XKIRO_API_KEY else None

# 🔥 Same Magic: Fetch live models to prevent 404 errors!
def get_dynamic_models():
    print("🔍 Scanning xKiro API for live free models (for Auto-Topic)...")
    try:
        models_data = client.models.list()
        all_models = [m.id for m in models_data.data]
        
        best_keywords = ["qwen", "deepseek", "flash", "claude", "gpt", "llama"]
        prioritized = []
        
        for keyword in best_keywords:
            for m in all_models:
                if keyword in m.lower() and m not in prioritized:
                    prioritized.append(m)
                    
        for m in all_models:
            if m not in prioritized:
                prioritized.append(m)
                
        return prioritized[:10] # Top 10 live models
        
    except Exception as e:
        print(f"⚠️ Warning: Auto-fetch failed. Using smart fallbacks.")
        return ["qwen-2.5-72b", "deepseek-chat", "gpt-4o-mini", "llama-3.1-70b"]

def main():
    if not client: 
        print("❌ ERROR: XKIRO_API_KEY missing!")
        return
        
    with open("client_setup.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        
    old_topic = config.get("topic", "")
    print(f"🔄 Generating New Topic (Old was: {old_topic})...")
    
    prompt = f"Give me a NEW, unique 1-sentence story idea for a YouTube short video. It must involve the characters: '{config.get('character_anchor', '')}'. It must be different from: '{old_topic}'. Reply ONLY with the new topic sentence. No markdown, no quotes."
    
    dynamic_models = get_dynamic_models()
    
    for model in dynamic_models:
        print(f"🔄 Trying model: {model}...")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9
            )
            
            new_topic = response.choices[0].message.content.strip().replace('"', '')
            
            # Validation (Kam se kam 10 characters hone chahiye)
            if len(new_topic) > 10:
                config["topic"] = new_topic
                
                with open("client_setup.json", "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4)
                    
                print(f"✅ Successfully updated client_setup.json with NEW topic: {new_topic}")
                return # Success milte hi loop band
            else:
                print("⚠️ Output too short, trying next model...")
                
        except Exception as e:
            print(f"⚠️ Model Failed: {str(e)[:100]}... Moving to next.")
            time.sleep(2) # 2 sec aaram
            
    print("❌ All models failed to generate a new topic.")

if __name__ == "__main__":
    main()
