import os
import json
import subprocess
import urllib.request

try:
    from rembg import remove
except ImportError:
    subprocess.run(["pip", "install", "rembg", "onnxruntime", "pillow"])
    from rembg import remove

IMAGE_DIR, AUDIO_DIR, SFX_DIR, OUTPUT_DIR = "scene_images", "audio_clips", "sfx_clips", "final_output"
SCRIPT_FILE, TIMESTAMPS_FILE, CONFIG_FILE = "script_data.json", "audio_timestamps.json", "client_setup.json"
FONT_FILE = "Montserrat-Black.ttf"
BGM_FILE = os.path.join(SFX_DIR, "auto_bgm.mp3")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_assets():
    if not os.path.exists(FONT_FILE):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat-Black.ttf", FONT_FILE)

def create_parallax_layers(img_path, scene_id):
    fg_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}_fg.png")
    if not os.path.exists(fg_path):
        try:
            with open(img_path, 'rb') as i:
                with open(fg_path, 'wb') as o: o.write(remove(i.read()))
        except: return img_path, None
    return img_path, fg_path

def get_video_dimensions():
    with open(CONFIG_FILE, "r") as f:
        return (1080, 1920) if json.load(f).get("video_format", "long").lower() == "short" else (1920, 1080)

def create_scene_clip(scene_id, scene_data, duration, width, height):
    text = scene_data.get("narration", "")
    
    img_path, fg_path = create_parallax_layers(os.path.join(IMAGE_DIR, f"scene_{scene_id}.jpg"), scene_id)
    audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")
    sfx_path = os.path.join(SFX_DIR, f"sfx_scene_{scene_id}.mp3")
    out_path = os.path.join(OUTPUT_DIR, f"clip_{scene_id}.mp4")
    
    frames = int((duration + 1.0) * 25) # Add 1 sec buffer
    
    # 🔥 FIX 1: PERFECT 9:16 CROP (NO STRETCH/CHAPTI IMAGE)
    bg_filter = f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},gblur=sigma=10,zoompan=z='min(zoom+0.0005,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}[bg];"
    
    # 🔥 FIX 2: SEQUENTIAL ENTRY (Pehle Background, Fir 0.5s baad Insaan)
    if fg_path and os.path.exists(fg_path):
        fg_filter = f"[1:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},format=rgba[fg];[bg][fg]overlay=x=0:y='max(0, h - (t-0.5)*3000)':enable='gt(t,0.5)'[comp];"
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-loop", "1", "-i", fg_path]
        a_idx, sfx_idx = 2, 3
    else:
        fg_filter = ""
        bg_filter = bg_filter.replace("[bg]", "[comp]")
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path]
        a_idx, sfx_idx = 1, 2

    cmd.extend(["-i", audio_path])
    
    # Text Karaoke Style (Appears smoothly)
    clean_text = text.replace("'", "").replace(":", r"\:")
    fontsize = 80 if width == 1080 else 90
    text_y = (height / 2) + 300 if width == 1080 else (height / 2) + 250
    text_filter = f"[comp]drawtext=fontfile={FONT_FILE}:text='{clean_text}':fontcolor=#00FFFF:fontsize={fontsize}:borderw=5:bordercolor=black:shadowcolor=black@0.9:shadowx=5:shadowy=5:box=1:boxcolor=black@0.4:boxborderw=10:x=(w-text_w)/2:y={text_y}:enable='gt(t,0.5)'[v_out]"
    
    v_filter = bg_filter + fg_filter + text_filter

    # 🔥 FIX 3: LOUD AUDIO MIXING (NO MUTE BUG)
    if os.path.exists(sfx_path):
        cmd.extend(["-i", sfx_path])
        # Voice (200%), SFX (100% with delay to match hero entry at 0.5s)
        a_filter = f"[{a_idx}:a]volume=2.0[voice];[{sfx_idx}:a]adelay=500|500,volume=1.0[sfx];[voice][sfx]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[a_out]"
        cmd.extend(["-filter_complex", f"{v_filter};{a_filter}", "-map", "[v_out]", "-map", "[a_out]"])
    else:
        a_filter = f"[{a_idx}:a]volume=2.0[a_out]"
        cmd.extend(["-filter_complex", f"{v_filter};{a_filter}", "-map", "[v_out]", "-map", "[a_out]"])
        
    cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", "-t", str(duration + 1.0), "-pix_fmt", "yuv420p", "-preset", "fast", out_path])
    
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path

def main():
    download_assets()
    if not os.path.exists(TIMESTAMPS_FILE): return
        
    with open(TIMESTAMPS_FILE, "r") as f: timestamps = json.load(f)
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f: scenes = json.load(f)
    
    width, height = get_video_dimensions()
    clip_list = []
    
    for scene in scenes:
        scene_id = str(scene["scene"])
        duration = timestamps.get(scene_id)
        if duration and os.path.exists(os.path.join(IMAGE_DIR, f"scene_{scene_id}.jpg")):
            clip_list.append(create_scene_clip(scene_id, scene, duration, width, height))
        
    list_txt = os.path.join(OUTPUT_DIR, "concat.txt")
    with open(list_txt, "w") as f:
        for c in clip_list: f.write(f"file '{os.path.abspath(c)}'\n")
            
    temp_video = os.path.join(OUTPUT_DIR, "TEMP_MASTERPIECE.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-c:v", "copy", "-c:a", "aac", "-ar", "44100", "-ac", "2", temp_video], check=True)

    final_output = os.path.join(OUTPUT_DIR, "FINAL_AGENCY_MASTERPIECE.mp4")
    if os.path.exists(BGM_FILE):
        print("🎵 Adding LOUD Cinematic BGM...")
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_video, "-stream_loop", "-1", "-i", BGM_FILE, 
            "-filter_complex", "[1:a]volume=0.3[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]", 
            "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", final_output
        ], check=True)
    else:
        os.rename(temp_video, final_output)
        
    print(f"🎉 BOOM! Error-Free Video Ready: {final_output}")

if __name__ == "__main__":
    main()
