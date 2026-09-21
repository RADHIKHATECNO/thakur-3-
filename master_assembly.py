import os
import json
import subprocess
import urllib.request

# AI Background Remover Import
try:
    from rembg import remove
except ImportError:
    print("⏳ Installing rembg AI dynamically...")
    subprocess.run(["pip", "install", "rembg", "onnxruntime"])
    from rembg import remove

IMAGE_DIR = "scene_images"
AUDIO_DIR = "audio_clips"
SFX_DIR = "sfx_clips"
OUTPUT_DIR = "final_output"
SCRIPT_FILE = "script_data.json"
TIMESTAMPS_FILE = "audio_timestamps.json"
CONFIG_FILE = "client_setup.json"
FONT_FILE = "Anton-Regular.ttf"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Viral "MrBeast" Font auto-download
def download_viral_font():
    if not os.path.exists(FONT_FILE):
        print("📥 Downloading Viral 'Anton' Font...")
        url = "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf"
        urllib.request.urlretrieve(url, FONT_FILE)

# AI Cutout Generator
def create_parallax_layers(img_path, scene_id):
    fg_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}_fg.png")
    
    if not os.path.exists(fg_path):
        print(f"✂️ AI Cutting foreground for Scene {scene_id}...")
        with open(img_path, 'rb') as i:
            with open(fg_path, 'wb') as o:
                o.write(remove(i.read()))
    return img_path, fg_path

def get_video_dimensions():
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
        fmt = config.get("video_format", "long").lower()
        if fmt == "short":
            return 1080, 1920
        return 1920, 1080

def create_scene_clip(scene_id, text, duration, width, height):
    img_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}.jpg")
    audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")
    sfx_path = os.path.join(SFX_DIR, f"sfx_scene_{scene_id}.mp3")
    out_path = os.path.join(OUTPUT_DIR, f"clip_{scene_id}.mp4")
    
    # Hero cutout layer generate karein
    bg_path, fg_path = create_parallax_layers(img_path, scene_id)
    
    frames = int(duration * 25)
    
    # 1. Background (Blur + Slow Zoom)
    bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=8,zoompan=z='min(zoom+0.0005,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}[bg];"
    
    # 2. Foreground (Drop-in Animation from top in 0.5 seconds)
    fg_filter = f"[1:v]scale={width}:{height}[fg];[bg][fg]overlay=x=0:y='if(lt(t,0.5), -h+(h*t*2), 0)'[comp];"
    
    # 3. Viral Text (Yellow + Thick Black Border + Pop at 0.5s)
    clean_text = text.replace("'", "").replace(":", r"\:")
    fontsize = 85 if width == 1080 else 100
    text_y = "(h-text_h)/2+400" if width == 1080 else "(h-text_h)/2+300"
    
    # enable='gt(t,0.5)' ka matlab hai text tab aayega jab Hero neeche gir chuka hoga!
    text_filter = f"[comp]drawtext=fontfile={FONT_FILE}:text='{clean_text}':fontcolor=#FFE800:fontsize={fontsize}:borderw=8:bordercolor=black:shadowcolor=black:shadowx=5:shadowy=5:x=(w-text_w)/2:y={text_y}:enable='gt(t,0.5)'[v]"
    
    v_filter = bg_filter + fg_filter + text_filter
    
    # FFmpeg Command
    cmd = [
        "ffmpeg", "-y", 
        "-loop", "1", "-i", bg_path, 
        "-loop", "1", "-i", fg_path, 
        "-i", audio_path
    ]
    
    # Agar SFX hai toh usko 0.5s par bajayenge taaki drop ke saath sync ho!
    if os.path.exists(sfx_path):
        cmd.extend(["-i", sfx_path])
        # Voice = loud, SFX = medium (adelay=500 delays SFX by 0.5s to match drop)
        filter_complex = f"[2:a]volume=1.2[voice];[3:a]adelay=500|500,volume=0.6[sfx];[voice][sfx]amix=inputs=2:duration=first[aout]"
        cmd.extend(["-filter_complex", filter_complex, "-map", "[v]", "-map", "[aout]"])
    else:
        cmd.extend(["-map", "[v]", "-map", "2:a"])
        
    cmd.extend([
        "-filter_complex", v_filter if not os.path.exists(sfx_path) else v_filter.replace("[v]", "[v_out]", 1), 
        "-map", "[v]" if not os.path.exists(sfx_path) else "[v_out]",
        "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration), "-pix_fmt", "yuv420p", "-preset", "fast", out_path
    ])
    
    # Fix mapping edge case when audio complex filter is used
    if os.path.exists(sfx_path):
        cmd[cmd.index("-filter_complex")] = "-filter_complex"
        cmd[cmd.index(filter_complex)] = v_filter + filter_complex
        cmd[cmd.index("-map") + 1] = "[v]"

    print(f"🎬 Editing Scene {scene_id} [Parallax + Cutout + Drop-In + Viral Text]...")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path

def main():
    download_viral_font()
    
    if not os.path.exists(TIMESTAMPS_FILE):
        print("❌ ERROR: Timestamps missing!")
        return
        
    with open(TIMESTAMPS_FILE, "r") as f:
        timestamps = json.load(f)
        
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        scenes = {str(s["scene"]): s["narration"] for s in json.load(f)}
        
    width, height = get_video_dimensions()
    clip_list = []
    
    for scene_id, duration in timestamps.items():
        text = scenes.get(scene_id, "")
        clip = create_scene_clip(scene_id, text, duration, width, height)
        clip_list.append(clip)
        print(f"✅ Mastered Scene {scene_id} ({duration}s)")
        
    list_txt = os.path.join(OUTPUT_DIR, "concat.txt")
    with open(list_txt, "w") as f:
        for c in clip_list: 
            f.write(f"file '{os.path.abspath(c)}'\n")
            
    final_output = os.path.join(OUTPUT_DIR, "FINAL_AGENCY_MASTERPIECE.mp4")
    print("🔥 Merging 2.5D Parallax Clips into Final Masterpiece...")
    
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-c", "copy", final_output], check=True)
    print(f"🎉 BOOM! Viral Level Video is Ready: {final_output}")

if __name__ == "__main__":
    main()
