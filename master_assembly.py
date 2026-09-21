import os
import json
import subprocess
import urllib.request
import random
from PIL import Image

try:
    from rembg import remove
except ImportError:
    print("⏳ Installing rembg AI dynamically...")
    subprocess.run(["pip", "install", "rembg", "onnxruntime", "pillow"])
    from rembg import remove

IMAGE_DIR = "scene_images"
AUDIO_DIR = "audio_clips"
SFX_DIR = "sfx_clips"
OUTPUT_DIR = "final_output"
SCRIPT_FILE = "script_data.json"
TIMESTAMPS_FILE = "audio_timestamps.json"
CONFIG_FILE = "client_setup.json"
FONT_FILE = "Anton-Regular.ttf"
BGM_FILE = os.path.join(SFX_DIR, "auto_bgm.mp3")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_viral_font():
    if not os.path.exists(FONT_FILE):
        print("📥 Downloading Viral 'Anton' Font...")
        urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf", FONT_FILE)

def create_parallax_layers(img_path, scene_id):
    fg_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}_fg.png")
    if not os.path.exists(fg_path):
        try:
            print(f"✂️ AI Cutting foreground for Scene {scene_id}...")
            with open(img_path, 'rb') as i:
                with open(fg_path, 'wb') as o:
                    o.write(remove(i.read()))
        except Exception as e:
            print(f"⚠️ Rembg failed for scene {scene_id}.")
            return img_path, None
    return img_path, fg_path

# 🔥 THE MAGIC: Check karta hai ki cutout mein character hai ya khali hai!
def has_valid_character(fg_path):
    if not fg_path or not os.path.exists(fg_path):
        return False
    try:
        with Image.open(fg_path) as img:
            bbox = img.getbbox() # Check bounding box of non-transparent pixels
            if not bbox:
                return False
            # Check if the cutout is reasonably large (at least 5% of screen)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            area = width * height
            total_area = img.width * img.height
            if area < (total_area * 0.05): 
                return False
            return True
    except:
        return False

def get_video_dimensions():
    with open(CONFIG_FILE, "r") as f:
        fmt = json.load(f).get("video_format", "long").lower()
        return (1080, 1920) if fmt == "short" else (1920, 1080)

def create_scene_clip(scene_id, text, duration, width, height):
    img_path, fg_path = create_parallax_layers(os.path.join(IMAGE_DIR, f"scene_{scene_id}.jpg"), scene_id)
    audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")
    sfx_path = os.path.join(SFX_DIR, f"sfx_scene_{scene_id}.mp3")
    out_path = os.path.join(OUTPUT_DIR, f"clip_{scene_id}.mp4")
    
    frames = int(duration * 25)
    moves = ['zoom_in', 'pan_left', 'pan_right']
    move = random.choice(moves)
    
    has_char = has_valid_character(fg_path)
    
    if has_char:
        # ==========================================
        # 🔥 3D PARALLAX MODE (Smooth)
        # ==========================================
        print(f"🦸‍♂️ Character Detected in Scene {scene_id} -> Applying 3D Parallax!")
        if move == 'zoom_in':
            bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=5,zoompan=z='min(zoom+0.0005,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}[bg];"
        elif move == 'pan_left':
            bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=5,zoompan=z=1.15:d={frames}:x='max(0, iw/2-(iw/zoom/2)-on)':y='ih/2-(ih/zoom/2)':s={width}x{height}[bg];"
        else:
            bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=5,zoompan=z=1.15:d={frames}:x='min(iw-(iw/zoom), iw/2-(iw/zoom/2)+on)':y='ih/2-(ih/zoom/2)':s={width}x{height}[bg];"

        # Character super smoothly fade-in hoga bina hile (True depth illusion)
        fg_filter = f"[1:v]scale={width}:{height},format=rgba,fade=t=in:st=0:d=1:alpha=1[fg];[bg][fg]overlay=0:0[comp];"
        base_video_filter = bg_filter + fg_filter
        
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-loop", "1", "-i", fg_path]
        audio_idx = 2
        sfx_idx = 3
    else:
        # ==========================================
        # 🌄 NORMAL CINEMATIC MODE (Scenery/No Character)
        # ==========================================
        print(f"🌄 No Character in Scene {scene_id} -> Applying Cinematic Pan/Zoom.")
        if move == 'zoom_in':
            base_video_filter = f"[0:v]scale={width}:{height},zoompan=z='min(zoom+0.0005,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}[comp];"
        elif move == 'pan_left':
            base_video_filter = f"[0:v]scale={width}:{height},zoompan=z=1.15:d={frames}:x='max(0, iw/2-(iw/zoom/2)-on)':y='ih/2-(ih/zoom/2)':s={width}x{height}[comp];"
        else:
            base_video_filter = f"[0:v]scale={width}:{height},zoompan=z=1.15:d={frames}:x='min(iw-(iw/zoom), iw/2-(iw/zoom/2)+on)':y='ih/2-(ih/zoom/2)':s={width}x{height}[comp];"
            
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path]
        audio_idx = 1
        sfx_idx = 2

    cmd.extend(["-i", audio_path])
    
    # ==========================================
    # 🔥 VIRAL TEXT ENGINE
    # ==========================================
    clean_text = text.replace("'", "").replace(":", r"\:")
    fontsize = 80 if width == 1080 else 90
    text_y = "(h-text_h)/2+400" if width == 1080 else "(h-text_h)/2+300"
    
    text_filter = f"[comp]drawtext=fontfile={FONT_FILE}:text='{clean_text}':fontcolor=#FFE800:fontsize={fontsize}:borderw=4:bordercolor=black:shadowcolor=black@0.8:shadowx=6:shadowy=6:box=1:boxcolor=black@0.4:boxborderw=10:x=(w-text_w)/2:y='max({text_y}, {text_y}+50-(t*100))'[v_out]"
    
    v_filter = base_video_filter + text_filter

    # ==========================================
    # 🎵 AUDIO MIXING
    # ==========================================
    if os.path.exists(sfx_path):
        cmd.extend(["-i", sfx_path])
        a_filter = f"[{audio_idx}:a]volume=1.2[voice];[{sfx_idx}:a]volume=0.4[sfx];[voice][sfx]amix=inputs=2:duration=first[a_out]"
        cmd.extend(["-filter_complex", f"{v_filter};{a_filter}", "-map", "[v_out]", "-map", "[a_out]"])
    else:
        cmd.extend(["-filter_complex", v_filter, "-map", "[v_out]", "-map", f"{audio_idx}:a"])
        
    cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-t", str(duration), "-pix_fmt", "yuv420p", "-preset", "fast", out_path])
    
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path

def main():
    download_viral_font()
    if not os.path.exists(TIMESTAMPS_FILE): return
        
    with open(TIMESTAMPS_FILE, "r") as f: timestamps = json.load(f)
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f: scenes = {str(s["scene"]): s["narration"] for s in json.load(f)}
    width, height = get_video_dimensions()
    
    clip_list = []
    for scene_id, duration in timestamps.items():
        if os.path.exists(os.path.join(IMAGE_DIR, f"scene_{scene_id}.jpg")) and os.path.exists(os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")):
            clip_list.append(create_scene_clip(scene_id, scenes.get(scene_id, ""), duration, width, height))
        
    list_txt = os.path.join(OUTPUT_DIR, "concat.txt")
    with open(list_txt, "w") as f:
        for c in clip_list: f.write(f"file '{os.path.abspath(c)}'\n")
            
    temp_video = os.path.join(OUTPUT_DIR, "TEMP_MASTERPIECE.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-c", "copy", temp_video], check=True)

    final_output = os.path.join(OUTPUT_DIR, "FINAL_AGENCY_MASTERPIECE.mp4")
    
    if os.path.exists(BGM_FILE):
        print("🎵 Adding Cinematic Background Music...")
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_video, "-stream_loop", "-1", "-i", BGM_FILE, 
            "-filter_complex", "[1:a]volume=0.08[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]", 
            "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", final_output
        ], check=True)
    else:
        os.rename(temp_video, final_output)
        
    print(f"🎉 BOOM! Ultra-Smooth Smart Parallax Video Ready: {final_output}")

if __name__ == "__main__":
    main()
