import os
import json
import requests
import time
import re

SCRIPT_FILE = "script_data.json"
SFX_DIR = "sfx_clips"
FREESOUND_API_KEY = os.getenv("FREESOUND_API_KEY")

os.makedirs(SFX_DIR, exist_ok=True)

def download_sound(query, filename, min_duration=1, max_duration=10): # Duration thodi badha di hai taaki aur sounds mil sakein
    if not FREESOUND_API_KEY: 
        return False
    
    # 🔥 THE MAGIC FIX: Extract only the first 1-2 words from long AI sentences!
    # Split by comma and take the first part
    clean_query = re.split(r'[,;|\.]', query)[0].strip() 
    words = clean_query.split()
    
    if len(words) > 2:
        clean_query = " ".join(words[:2]) # Sirf pehle 2 words lega
        
    print(f"🔍 Original SFX: '{query[:40]}...' | Searching Freesound for: '{clean_query}'...")
    
    url = "https://freesound.org/apiv2/search/text/"
    params = {
        "query": clean_query, 
        "token": FREESOUND_API_KEY, 
        "fields": "id,name,previews", 
        "filter": f"duration:[{min_duration} TO {max_duration}]", 
        "page_size": 1
    }
    
    try:
        # ATTEMPT 1: Try with 2 words
        data = requests.get(url, params=params).json()
        
        if data.get("results") and len(data["results"]) > 0:
            sfx_data = requests.get(data["results"][0]["previews"]["preview-hq-mp3"]).content
            with open(filename, "wb") as f: f.write(sfx_data)
            print(f"✅ Downloaded: {data['results'][0]['name']}")
            return True
        else:
            # ATTEMPT 2: Fallback to just the FIRST single word (Ultimate backup)
            if len(words) > 1:
                print(f"⚠️ Not found. Retrying with single word: '{words[0]}'...")
                params["query"] = words[0]
                data = requests.get(url, params=params).json()
                
                if data.get("results") and len(data["results"]) > 0:
                    sfx_data = requests.get(data["results"][0]["previews"]["preview-hq-mp3"]).content
                    with open(filename, "wb") as f: f.write(sfx_data)
                    print(f"✅ Downloaded Fallback: {data['results'][0]['name']}")
                    return True
                    
    except Exception as e: 
        pass
        
    print(f"❌ Could not find any sound. Skipping this SFX.")
    return False

def main():
    print("🎵 Downloading Cinematic Background Music...")
    # BGM ke liye 30-180 sec lamba track
    download_sound("cinematic suspense drone", os.path.join(SFX_DIR, "auto_bgm.mp3"), 30, 180)
    
    if os.path.exists(SCRIPT_FILE):
        with open(SCRIPT_FILE, "r", encoding="utf-8") as f: 
            scenes = json.load(f)
            
        for scene in scenes:
            sfx_tag = scene.get("sfx")
            if sfx_tag and str(sfx_tag).strip().lower() not in ["none", "null", "", "n/a"]:
                download_sound(sfx_tag, os.path.join(SFX_DIR, f"sfx_scene_{scene.get('scene')}.mp3"), 1, 10)
                time.sleep(1.5) # API Rate limit protection

if __name__ == "__main__":
    main()
