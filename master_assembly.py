import os
import json
import subprocess
import urllib.request
from PIL import Image

try:
    from rembg import remove
except ImportError:
    subprocess.run(["pip", "install", "rembg", "onnxruntime", "pillow"])
    from rembg import remove

IMAGE_DIR, AUDIO_DIR, SFX_DIR, OUTPUT_DIR = "scene_images", "audio_clips", "sfx_clips", "final_output"
SCRIPT_FILE, TIMESTAMPS_FILE, CONFIG_FILE = "script_data.json", "audio_timestamps.json", "client_setup.json"
FONT_FILE = "Anton-Regular.ttf"
BGM_FILE = os.path.join(SFX_DIR, "auto_bgm.mp3")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_viral_font():
    if not os.path.exists(FONT_FILE):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf", FONT_FILE)

def create_parallax_layers(img_path, scene_id):
    fg_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}_fg.png")
    if not os.path.exists(fg_path):
        try:
            with open(img_path, 'rb') as i:
                with open(fg_path, 'wb') as o: o.write(remove(i.read()))
        except: return img_path, None
    return img_path, fg_path

def has_valid_character(fg_path):
    if not fg_path or not os.path.exists(fg_path): return False
    try:
        with Image.open(fg_path) as img:
            bbox = img.getbbox()
            if not bbox: return False
            area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            return area > (img.width * img.height * 0.05)
    except: return False

def get_video_dimensions():
    with open(CONFIG_FILE, "r") as f:
        return (1080, 1920) if json.load(f).get("video_format", "long").lower() == "short" else (1920, 1080)

def create_scene_clip(scene_id, scene_data, duration, width, height):
    text = scene_data.get("narration", "")
    anim_style = scene_data.get("animation", "zoom_in") # AI se animation style lega
    
    img_path, fg_path = create_parallax_layers(os.path.join(IMAGE_DIR, f"scene_{scene_id}.jpg"), scene_id)
    audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")
    sfx_path = os.path.join(SFX_DIR, f"sfx_scene_{scene_id}.mp3")
    out_path = os.path.join(OUTPUT_DIR, f"clip_{scene_id}.mp4")
    
    frames = int(duration * 25)
    has_char = has_valid_character(fg_path)
    
    if has_char:
        # 🔥 STORY-DRIVEN PARALLAX MATH
        if anim_style == 'fly_up':
            bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=4,zoompan=z=1.1:d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'[bg];"
            fg_filter = f"[1:v]scale={width}:{height},format=rgba[fg];[bg][fg]overlay=x=0:y='max(-h/2, h/4 - (t*150))'[comp];"
        
        elif anim_style == 'drive_forward':
            # Background moves backward, Foreground zooms in fast
            bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=3,zoompan=z='max(1.0, 1.2-(0.001*on))':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'[bg];"
            fg_filter = f"[1:v]scale={width}:{height},format=rgba,zoompan=z='min(1.5, 1.0+(0.005*on))':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',format=rgba[fg];[bg][fg]overlay=0:0[comp];"
            
        elif anim_style == 'slide_left':
            bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=5,zoompan=z=1.1:d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'[bg];"
            fg_filter = f"[1:v]scale={width}:{height},format=rgba[fg];[bg][fg]overlay=x='max(0, w - (t*800))':y=0[comp];"
            
        elif anim_style == 'float_clouds':
            # Background slowly pans horizontally like clouds
            bg_filter = f"[0:v]scale={width}:{height},zoompan=z=1.2:d={frames}:x='on*2':y='ih/2-(ih/zoom/2)'[bg];"
            fg_filter = f"[1:v]scale={width}:{height},format=rgba[fg];[bg][fg]overlay=0:'sin(t*2)*10'[comp];"
            
        else: # Default zoom_in
            bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=5,zoompan=z='min(zoom+0.0005,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'[bg];"
            fg_filter = f"[1:v]scale={width}:{height},format=rgba,fade=t=in:st=0:d=1:alpha=1[fg];[bg][fg]overlay=0:0[comp];"
            
        base_video_filter = bg_filter + fg_filter
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-loop", "1", "-i", fg_path]
        audio_idx, sfx_idx = 2, 3
    else:
        # Fallback for Scenery
        base_video_filter = f"[0:v]scale={width}:{height},zoompan=z='min(zoom+0.0005,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'[comp];"
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path]
        audio_idx, sfx_idx = 1, 2

    cmd.extend(["-i", audio_path])
    
    # 🔥 SMOOTH SCROLLING TEXT (Neeche se aaram se upar aayega)
    clean_text = text.replace("'", "").replace(":", r"\:")
    fontsize = 75 if width == 1080 else 85
    text_end_y = (height / 2) + 300 if width == 1080 else (height / 2) + 250
    
    # Text Y-axis par smooth equation: Start bottom, scroll up slowly
    text_filter = f"[comp]drawtext=fontfile={FONT_FILE}:text='{clean_text}':fontcolor=#FFFFFF:fontsize={fontsize}:borderw=4:bordercolor=black:shadowcolor=black@0.8:shadowx=6:shadowy=6:x=(w-text_w)/2:y='max({text_end_y}, h - (t*200))'[v_out]"
    
    v_filter = base_video_filter + text_filter

    # Audio Mixing
    if os.path.exists(sfx_path):
        cmd.extend(["-i", sfx_path])
        a_filter = f"[{audio_idx}:a]volume=1.2[voice];[{sfx_idx}:a]volume=0.4[sfx];[voice][sfx]amix=inputs=2:duration=first[a_out]"
        cmd.extend(["-filter_complex", f"{v_filter};{a_filter}", "-map", "[v_out]", "-map", "[a_out]"])
    else:
        cmd.extend(["-filter_complex", v_filter, "-map", "[v_out]", "-map", f"{audio_idx}:a"])
        
    cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-t", str(duration), "-pix_fmt", "yuv420p", "-preset", "fast", out_path])
    
    print(f"🎬 Editing Scene {scene_id} [Style: {anim_style.upper()}]...")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path

def main():
    download_viral_font()
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
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-c", "copy", temp_video], check=True)

    final_output = os.path.join(OUTPUT_DIR, "FINAL_AGENCY_MASTERPIECE.mp4")
    bgm_path = os.path.join(SFX_DIR, "auto_bgm.mp3")
    
    if os.path.exists(bgm_path):
        print("🎵 Adding Cinematic BGM...")
        subprocess.run(["ffmpeg", "-y", "-i", temp_video, "-stream_loop", "-1", "-i", bgm_path, "-filter_complex", "[1:a]volume=0.08[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]", "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", final_output], check=True)
    else:
        os.rename(temp_video, final_output)
        
    print(f"🎉 BOOM! Context-Aware Video Ready: {final_output}")

if __name__ == "__main__":
    main()
