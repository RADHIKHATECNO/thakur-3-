import os
import json
import requests
import time

SCRIPT_FILE = "script_data.json"
SFX_DIR = "sfx_clips"

# Freesound API Key (Free of cost from freesound.org)
FREESOUND_API_KEY = os.getenv("FREESOUND_API_KEY")

os.makedirs(SFX_DIR, exist_ok=True)

def download_sfx(query, scene_id):
    if not FREESOUND_API_KEY:
        print("⚠️ FREESOUND_API_KEY missing! SFX skip ho raha hai.")
        return False
        
    print(f"🔍 Searching live internet for SFX: '{query}'...")
    
    search_url = "https://freesound.org/apiv2/search/text/"
    params = {
        "query": query,
        "token": FREESOUND_API_KEY,
        "fields": "id,name,previews",
        "filter": "duration:[1.0 TO 5.0]", # 1 se 5 second ke sound chahiye
        "page_size": 1
    }
    
    try:
        response = requests.get(search_url, params=params)
        data = response.json()
        
        if data.get("results"):
            # High-quality MP3 preview URL nikalna
            preview_url = data["results"][0]["previews"]["preview-hq-mp3"]
            sfx_path = os.path.join(SFX_DIR, f"sfx_scene_{scene_id}.mp3")
            
            # Sound Download karna
            sfx_data = requests.get(preview_url).content
            with open(sfx_path, "wb") as f:
                f.write(sfx_data)
                
            print(f"✅ Downloaded SFX for Scene {scene_id}: {data['results'][0]['name']}")
            return True
        else:
            print(f"⚠️ No sound found for '{query}'")
            return False
            
    except Exception as e:
        print(f"❌ SFX Download failed: {e}")
        return False
        
def main():
    if not os.path.exists(SCRIPT_FILE):
        print("❌ ERROR: script_data.json nahi mili!")
        return
        
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        scenes = json.load(f)
        
    for scene in scenes:
        sfx_tag = scene.get("sfx")
        scene_id = scene.get("scene")
        
        # Agar script mein koi SFX likha hai aur wo khaali nahi hai
        if sfx_tag and str(sfx_tag).strip().lower() != "none":
            download_sfx(sfx_tag, scene_id)
            time.sleep(1) # API limit se bachne ke liye 1 second ka gap
            
if __name__ == "__main__":
    main()
