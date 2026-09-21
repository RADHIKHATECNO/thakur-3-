import os
import json
import subprocess
import urllib.request
import random

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

def download_viral_font():
    if not os.path.exists(FONT_FILE):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf", FONT_FILE)

def create_parallax_layers(img_path, scene_id):
    fg_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}_fg.png")
    if not os.path.exists(fg_path):
        try:
            with open(img_path, 'rb') as i:
                with open(fg_path, 'wb') as o:
                    o.write(remove(i.read()))
        except Exception as e:
            print(f"⚠️ Rembg failed for scene {scene_id}, falling back to original image.")
            return img_path, img_path # Fallback if AI fails
    return img_path, fg_path

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
    
    # ==========================================
    # 🔥 1. RANDOM SMOOTH CAMERA MOVEMENTS
    # ==========================================
    camera_moves = ['zoom_in', 'pan_left', 'pan_right']
    move = random.choice(camera_moves)
    
    if move == 'zoom_in':
        # Dheere se aage aana (Smooth Zoom)
        bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=5,zoompan=z='min(zoom+0.0004,1.1)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}[bg];"
    elif move == 'pan_left':
        # Dheere se Left dekhna
        bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=5,zoompan=z=1.1:d={frames}:x='max(0, (iw/2-(iw/zoom/2)) - 0.5*t*25)':y='ih/2-(ih/zoom/2)':s={width}x{height}[bg];"
    else: # pan_right
        # Dheere se Right dekhna
        bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=5,zoompan=z=1.1:d={frames}:x='min(iw-(iw/zoom), (iw/2-(iw/zoom/2)) + 0.5*t*25)':y='ih/2-(ih/zoom/2)':s={width}x{height}[bg];"

    # ==========================================
    # 🔥 2. SMOOTH FADE-IN FOREGROUND (No Drop)
    # ==========================================
    # Character halke se transparency (opacity 0 se 1) ke sath 1 second me samne aayega
    fg_filter = f"[1:v]scale={width}:{height},format=rgba,colorchannelmixer=aa='min(t/1,1)'[fg];[bg][fg]overlay=0:0[comp];"
    
    # ==========================================
    # 🔥 3. PREMIUM SLIDING TEXT WITH SHADOW BOX
    # ==========================================
    clean_text = text.replace("'", "").replace(":", r"\:")
    fontsize = 80 if width == 1080 else 90
    text_y_target = "(h-text_h)/2+400" if width == 1080 else "(h-text_h)/2+300"
    
    # Text niche se halka sa upar slide karke set hoga
    text_filter = f"[comp]drawtext=fontfile={FONT_FILE}:text='{clean_text}':fontcolor=#FFE800:fontsize={fontsize}:borderw=4:bordercolor=black:shadowcolor=black@0.8:shadowx=6:shadowy=6:box=1:boxcolor=black@0.4:boxborderw=10:x=(w-text_w)/2:y='max({text_y_target}, {text_y_target}+50-(t*100))'[v_out]"
    
    # Combine Filters
    v_filter = bg_filter + fg_filter + text_filter
    
    # FFmpeg commands compilation
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-loop", "1", "-i", fg_path, "-i", audio_path]
    
    if os.path.exists(sfx_path):
        cmd.extend(["-i", sfx_path])
        # Sound ab bina delay ke smoothly fade-in ke sath bajega
        a_filter = "[2:a]volume=1.2[voice];[3:a]volume=0.4[sfx];[voice][sfx]amix=inputs=2:duration=first[a_out]"
        full_filter = f"{v_filter};{a_filter}"
        cmd.extend(["-filter_complex", full_filter, "-map", "[v_out]", "-map", "[a_out]"])
    else:
        cmd.extend(["-filter_complex", v_filter, "-map", "[v_out]", "-map", "2:a"])
        
    cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-t", str(duration), "-pix_fmt", "yuv420p", "-preset", "fast", out_path])
    
    print(f"🎬 Rendering Scene {scene_id} [Movement: {move.upper()} | Soft Fade-In]...")
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

    # 4. Auto BGM Mixing
    final_output = os.path.join(OUTPUT_DIR, "FINAL_AGENCY_MASTERPIECE.mp4")
    bgm_path = os.path.join(SFX_DIR, "auto_bgm.mp3")
    
    if os.path.exists(bgm_path):
        print("🎵 Adding Cinematic Background Music...")
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_video, "-stream_loop", "-1", "-i", bgm_path, 
            "-filter_complex", "[1:a]volume=0.08[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]", 
            "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", final_output
        ], check=True)
    else:
        os.rename(temp_video, final_output)
        
    print(f"🎉 BOOM! Ultra-Smooth Cinematic Video Ready: {final_output}")

if __name__ == "__main__":
    main()
