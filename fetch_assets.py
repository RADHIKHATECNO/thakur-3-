import os
import json
import requests
import time

SCRIPT_FILE = "script_data.json"
SFX_DIR = "sfx_clips"
FREESOUND_API_KEY = os.getenv("FREESOUND_API_KEY")

os.makedirs(SFX_DIR, exist_ok=True)

def download_sound(query, filename, min_duration=1, max_duration=5):
    if not FREESOUND_API_KEY: return False
    print(f"🔍 Searching Freesound for: '{query}'...")
    
    url = "https://freesound.org/apiv2/search/text/"
    params = {
        "query": query, "token": FREESOUND_API_KEY, 
        "fields": "id,name,previews", 
        "filter": f"duration:[{min_duration} TO {max_duration}]", 
        "page_size": 1
    }
    try:
        data = requests.get(url, params=params).json()
        if data.get("results"):
            sfx_data = requests.get(data["results"][0]["previews"]["preview-hq-mp3"]).content
            with open(filename, "wb") as f: f.write(sfx_data)
            print(f"✅ Downloaded: {data['results'][0]['name']}")
            return True
    except: pass
    return False

def main():
    # 1. Download Background Music (Long duration: 30 to 180 seconds)
    print("🎵 Downloading Cinematic Background Music...")
    download_sound("cinematic suspense drone", os.path.join(SFX_DIR, "auto_bgm.mp3"), 30, 180)
    
    # 2. Download Scene SFX
    if os.path.exists(SCRIPT_FILE):
        with open(SCRIPT_FILE, "r", encoding="utf-8") as f: scenes = json.load(f)
        for scene in scenes:
            sfx_tag = scene.get("sfx")
            if sfx_tag and str(sfx_tag).strip().lower() != "none":
                download_sound(sfx_tag, os.path.join(SFX_DIR, f"sfx_scene_{scene.get('scene')}.mp3"))
                time.sleep(1)

if __name__ == "__main__":
    main()
