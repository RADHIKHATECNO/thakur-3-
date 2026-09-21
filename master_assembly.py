import os
import json
import subprocess
import urllib.request
import cv2 
from PIL import Image

try:
    from rembg import remove
except ImportError:
    subprocess.run(["pip", "install", "rembg", "onnxruntime", "pillow", "opencv-python-headless"])
    from rembg import remove

IMAGE_DIR, AUDIO_DIR, SFX_DIR, OUTPUT_DIR = "scene_images", "audio_clips", "sfx_clips", "final_output"
SCRIPT_FILE, TIMESTAMPS_FILE, CONFIG_FILE = "script_data.json", "audio_timestamps.json", "client_setup.json"
FONT_FILE = "Anton-Regular.ttf"
CASCADE_FILE = "haarcascade_frontalface_default.xml"
BGM_FILE = os.path.join(SFX_DIR, "auto_bgm.mp3")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_assets():
    if not os.path.exists(FONT_FILE): urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf", FONT_FILE)
    if not os.path.exists(CASCADE_FILE): urllib.request.urlretrieve("https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml", CASCADE_FILE)

def get_face_focus_point(image_path):
    try:
        faces = cv2.CascadeClassifier(CASCADE_FILE).detectMultiScale(cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2GRAY), 1.1, 4)
        if len(faces) > 0:
            return f"x='{faces[0][0] + (faces[0][2] / 2)}-(iw/zoom/2)':y='{faces[0][1] + (faces[0][3] / 2)}-(ih/zoom/2)'"
    except: pass
    return "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"

def create_parallax_layers(scene_id):
    # 🔥 MAGIC: Cutout Asli RAW photo se banega!
    raw_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}_raw.jpg")
    img_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}.jpg")
    fg_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}_fg.png")
    
    if os.path.exists(raw_path) and not os.path.exists(fg_path):
        try:
            with open(raw_path, 'rb') as i:
                with open(fg_path, 'wb') as o: o.write(remove(i.read()))
        except: return img_path, None
    return img_path, fg_path

def has_valid_character(fg_path):
    if not fg_path or not os.path.exists(fg_path): return False
    try:
        with Image.open(fg_path) as img:
            bbox = img.getbbox()
            return bbox and ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) > (img.width * img.height * 0.05))
    except: return False

def get_video_dimensions():
    with open(CONFIG_FILE, "r") as f: return (1080, 1920) if json.load(f).get("video_format", "long").lower() == "short" else (1920, 1080)

def create_scene_clip(scene_id, scene_data, duration, width, height):
    text = scene_data.get("narration", "")
    anim_style = scene_data.get("animation", "zoom_in") 
    
    img_path, fg_path = create_parallax_layers(scene_id)
    audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")
    sfx_path = os.path.join(SFX_DIR, f"sfx_scene_{scene_id}.mp3")
    out_path = os.path.join(OUTPUT_DIR, f"clip_{scene_id}.mp4")
    
    frames = int((duration + 1.0) * 25)
    has_char = has_valid_character(fg_path)
    zoom_target = get_face_focus_point(img_path)
    
    if has_char:
        # 🔥 BACKGROUND EKDUM SAAF HAI ABU (Blur Hata Diya!)
        bg_filter = f"[0:v]scale={width}:{height},zoompan=z='min(zoom+0.0005,1.15)':d={frames}:{zoom_target}[bg];"
        
        if anim_style == 'slide_left':
            fg_filter = f"[1:v]scale={width}:{height}:force_original_aspect_ratio=decrease,format=rgba[fg];[bg][fg]overlay=x='max((W-w)/2, w - (t*2000))':y='(H-h)/2':enable='gt(t,0.3)'[comp];"
        elif anim_style == 'fly_up':
            fg_filter = f"[1:v]scale={width}:{height}:force_original_aspect_ratio=decrease,format=rgba[fg];[bg][fg]overlay=x='(W-w)/2':y='max((H-h)/2, h - (t*1500))':enable='gt(t,0.3)'[comp];"
        else: # Drop in / Zoom in
            fg_filter = f"[1:v]scale={width}:{height}:force_original_aspect_ratio=decrease,format=rgba,fade=t=in:st=0.3:d=0.5:alpha=1[fg];[bg][fg]overlay=x='(W-w)/2':y='(H-h)/2'[comp];"
            
        base_v = bg_filter + fg_filter
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-loop", "1", "-i", fg_path]
        a_idx, sfx_idx = 2, 3
    else:
        base_v = f"[0:v]scale={width}:{height},zoompan=z='min(zoom+0.0005,1.15)':d={frames}:{zoom_target}[comp];"
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path]
        a_idx, sfx_idx = 1, 2

    cmd.extend(["-i", audio_path])
    
    # TEXT
    cln_text = text.replace("'", "").replace(":", r"\:")
    tsz = 80 if width == 1080 else 90
    ty = (height / 2) + 300 if width == 1080 else (height / 2) + 250
    t_filter = f"[comp]drawtext=fontfile={FONT_FILE}:text='{cln_text}':fontcolor=#FFE800:fontsize={tsz}:borderw=4:bordercolor=black:shadowcolor=black@0.8:shadowx=6:shadowy=6:box=1:boxcolor=black@0.5:boxborderw=15:x=(w-text_w)/2:y='max({ty}, h - ((t-0.5)*300))':enable='gt(t,0.5)'[v_out]"
    
    # 🎧 FIX: AUDIO SYNC & LOUDNESS (44100Hz Standardized)
    if os.path.exists(sfx_path):
        cmd.extend(["-i", sfx_path])
        a_filter = f"[{a_idx}:a]adelay=700|700,volume=1.5[voice];[{sfx_idx}:a]adelay=300|300,volume=0.8[sfx];[voice][sfx]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[a_out]"
        cmd.extend(["-filter_complex", base_v + t_filter + ";" + a_filter, "-map", "[v_out]", "-map", "[a_out]"])
    else:
        a_filter = f"[{a_idx}:a]adelay=500|500,volume=1.5[a_out]"
        cmd.extend(["-filter_complex", base_v + t_filter + ";" + a_filter, "-map", "[v_out]", "-map", "[a_out]"])
        
    # Standardizing audio track so it doesn't get muted on concat!
    cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", "-t", str(duration + 1.0), "-pix_fmt", "yuv420p", "-preset", "fast", out_path])
    
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path

def main():
    download_assets()
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
    # Using specific audio rates in concat to stop mute bug!
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-c:v", "copy", "-c:a", "aac", "-ar", "44100", "-ac", "2", temp_video], check=True)

    final_output = os.path.join(OUTPUT_DIR, "FINAL_AGENCY_MASTERPIECE.mp4")
    if os.path.exists(BGM_FILE):
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_video, "-stream_loop", "-1", "-i", BGM_FILE, 
            "-filter_complex", "[1:a]volume=0.3[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]", 
            "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", final_output
        ], check=True)
    else:
        os.rename(temp_video, final_output)
        
    print(f"🎉 BOOM! Silent Audio & Double Head FIXED. Video Ready: {final_output}")

if __name__ == "__main__":
    main()
