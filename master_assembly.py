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
BGM_FILE = os.path.join(SFX_DIR, "auto_bgm.mp3") # Naya Auto BGM

os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_viral_font():
    if not os.path.exists(FONT_FILE):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf", FONT_FILE)

def create_parallax_layers(img_path, scene_id):
    fg_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}_fg.png")
    if not os.path.exists(fg_path):
        with open(img_path, 'rb') as i:
            with open(fg_path, 'wb') as o:
                o.write(remove(i.read()))
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
    
    # 1. Background (Blur + Slow Zoom)
    bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=8,zoompan=z='min(zoom+0.0005,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}[bg]"
    
    # 2. Random Dynamic Animation (Top, Bottom, Left, Right)
    animations = ['top', 'bottom', 'left', 'right']
    anim = random.choice(animations)
    
    if anim == 'top': overlay_expr = "x=0:y='min(0, -h+(h*t*2))'"
    elif anim == 'bottom': overlay_expr = "x=0:y='max(0, h-(h*t*2))'"
    elif anim == 'left': overlay_expr = "x='min(0, -w+(w*t*2))':y=0"
    elif anim == 'right': overlay_expr = "x='max(0, w-(w*t*2))':y=0"

    fg_filter = f"[1:v]scale={width}:{height}[fg];[bg][fg]overlay={overlay_expr}[comp]"
    
    # 3. Viral Text
    clean_text = text.replace("'", "").replace(":", r"\:")
    fontsize = 85 if width == 1080 else 100
    text_y = "(h-text_h)/2+400" if width == 1080 else "(h-text_h)/2+300"
    text_filter = f"[comp]drawtext=fontfile={FONT_FILE}:text='{clean_text}':fontcolor=#FFE800:fontsize={fontsize}:borderw=8:bordercolor=black:x=(w-text_w)/2:y={text_y}:enable='gt(t,0.5)'[v_out]"
    
    # Combine Video Filters safely
    v_filter = f"{bg_filter};{fg_filter};{text_filter}"
    
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-loop", "1", "-i", fg_path, "-i", audio_path]
    
    # Safely combine Audio Filters to fix Error 234
    if os.path.exists(sfx_path):
        cmd.extend(["-i", sfx_path])
        a_filter = "[2:a]volume=1.2[voice];[3:a]adelay=500|500,volume=0.6[sfx];[voice][sfx]amix=inputs=2:duration=first[a_out]"
        full_filter = f"{v_filter};{a_filter}"
        cmd.extend(["-filter_complex", full_filter, "-map", "[v_out]", "-map", "[a_out]"])
    else:
        cmd.extend(["-filter_complex", v_filter, "-map", "[v_out]", "-map", "2:a"])
        
    cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-t", str(duration), "-pix_fmt", "yuv420p", "-preset", "fast", out_path])
    
    print(f"🎬 Rendering Scene {scene_id} [Animation: {anim.upper()}]...")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path

def main():
    download_viral_font()
    with open(TIMESTAMPS_FILE, "r") as f: timestamps = json.load(f)
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f: scenes = {str(s["scene"]): s["narration"] for s in json.load(f)}
    width, height = get_video_dimensions()
    
    clip_list = []
    for scene_id, duration in timestamps.items():
        clip_list.append(create_scene_clip(scene_id, scenes.get(scene_id, ""), duration, width, height))
        
    list_txt = os.path.join(OUTPUT_DIR, "concat.txt")
    with open(list_txt, "w") as f:
        for c in clip_list: f.write(f"file '{os.path.abspath(c)}'\n")
            
    temp_video = os.path.join(OUTPUT_DIR, "TEMP_MASTERPIECE.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-c", "copy", temp_video], check=True)

    # 4. Auto BGM Mixing
    final_output = os.path.join(OUTPUT_DIR, "FINAL_AGENCY_MASTERPIECE.mp4")
    if os.path.exists(BGM_FILE):
        print("🎵 Adding Downloaded Auto-BGM to Final Video...")
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_video, "-stream_loop", "-1", "-i", BGM_FILE, 
            "-filter_complex", "[1:a]volume=0.08[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]", 
            "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", final_output
        ], check=True)
    else:
        os.rename(temp_video, final_output)
        
    print(f"🎉 BOOM! Final Video with BGM Ready: {final_output}")

if __name__ == "__main__":
    main()
