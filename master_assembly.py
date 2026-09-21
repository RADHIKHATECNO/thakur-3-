import os
import json
import subprocess
import urllib.request
import random
import cv2  # 🔥 OpenCV for Face Tracking!
from PIL import Image

try:
    from rembg import remove
except ImportError:
    subprocess.run(["pip", "install", "rembg", "onnxruntime", "pillow", "opencv-python-headless"])
    from rembg import remove

# --- DIRECTORIES ---
IMAGE_DIR, AUDIO_DIR, SFX_DIR, OUTPUT_DIR = "scene_images", "audio_clips", "sfx_clips", "final_output"
SCRIPT_FILE, TIMESTAMPS_FILE, CONFIG_FILE = "script_data.json", "audio_timestamps.json", "client_setup.json"

FONT_FILE = "Anton-Regular.ttf"
CASCADE_FILE = "haarcascade_frontalface_default.xml"
BGM_FILE = os.path.join(SFX_DIR, "auto_bgm.mp3")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 📥 DOWNLOAD REQUIRED ASSETS DYNAMICALLY
def download_assets():
    if not os.path.exists(FONT_FILE):
        print("📥 Downloading Viral Font...")
        urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf", FONT_FILE)
    if not os.path.exists(CASCADE_FILE):
        print("📥 Downloading OpenCV Face Tracker AI...")
        urllib.request.urlretrieve("https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml", CASCADE_FILE)

# 👁️ AI FACE TRACKER LOGIC
def get_face_focus_point(image_path, width, height):
    try:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(CASCADE_FILE)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) > 0:
            # Get the first face detected
            x, y, w, h = faces[0]
            # Find the center of the face
            face_center_x = x + (w / 2)
            face_center_y = y + (h / 2)
            print(f"🎯 FACE DETECTED at coordinates: X={face_center_x}, Y={face_center_y} -> Locking Camera!")
            # FFmpeg formula to center zoom on this exact point
            return f"x='{face_center_x}-(iw/zoom/2)':y='{face_center_y}-(ih/zoom/2)'"
    except Exception as e:
        print(f"⚠️ Face tracking failed: {e}")
        
    # Fallback to center zoom if no face is found
    return "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"

def create_parallax_layers(img_path, scene_id):
    fg_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}_fg.png")
    if not os.path.exists(fg_path):
        try:
            print(f"✂️ Extracting Hero for Scene {scene_id}...")
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
    anim_style = scene_data.get("animation", "zoom_in") 
    
    img_path, fg_path = create_parallax_layers(os.path.join(IMAGE_DIR, f"scene_{scene_id}.jpg"), scene_id)
    audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")
    sfx_path = os.path.join(SFX_DIR, f"sfx_scene_{scene_id}.mp3")
    out_path = os.path.join(OUTPUT_DIR, f"clip_{scene_id}.mp4")
    
    frames = int(duration * 25)
    has_char = has_valid_character(fg_path)
    
    # 👁️ FACE TRACKING ZOOM TARGET
    zoom_target = get_face_focus_point(img_path, width, height)
    
    # 🎧 8D SPATIAL AUDIO PANNING LOGIC
    audio_pan_filter = "pan=stereo|c0=c0|c1=c1" # Default (Center)
    
    if has_char:
        # 🔥 SEQUENTIAL ENTRY (0s: BG -> 0.5s: Hero Drops/Slides -> 1.0s: Voice starts)
        
        if anim_style == 'slide_left':
            bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=12,zoompan=z=1.1:d={frames}:{zoom_target}[bg];"
            fg_filter = f"[1:v]scale={width}:{height},format=rgba[fg];[bg][fg]overlay=x='max(0, w - (t*2000))':y=0:enable='gt(t,0.3)'[comp];"
            audio_pan_filter = "pan=stereo|c0=c0|c1=0.2*c1" # 8D Audio: Left Ear mostly
            
        elif anim_style == 'slide_right':
            bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=12,zoompan=z=1.1:d={frames}:{zoom_target}[bg];"
            fg_filter = f"[1:v]scale={width}:{height},format=rgba[fg];[bg][fg]overlay=x='min(0, -w + (t*2000))':y=0:enable='gt(t,0.3)'[comp];"
            audio_pan_filter = "pan=stereo|c0=0.2*c0|c1=c1" # 8D Audio: Right Ear mostly
            
        elif anim_style == 'fly_up':
            bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=12,zoompan=z=1.1:d={frames}:{zoom_target}[bg];"
            fg_filter = f"[1:v]scale={width}:{height},format=rgba[fg];[bg][fg]overlay=x=0:y='max(-h/2, h - (t*1500))':enable='gt(t,0.3)'[comp];"
            
        else: # Drop in / Zoom in
            bg_filter = f"[0:v]scale={width}:{height},gblur=sigma=12,zoompan=z='min(zoom+0.0005,1.15)':d={frames}:{zoom_target}[bg];"
            fg_filter = f"[1:v]scale={width}:{height},format=rgba,fade=t=in:st=0.3:d=0.5:alpha=1[fg];[bg][fg]overlay=0:0[comp];"
            
        base_video_filter = bg_filter + fg_filter
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-loop", "1", "-i", fg_path]
        audio_idx, sfx_idx = 2, 3
    else:
        # Fallback Scenery (Using Face Tracking if available, else center zoom)
        base_video_filter = f"[0:v]scale={width}:{height},zoompan=z='min(zoom+0.0005,1.15)':d={frames}:{zoom_target}[comp];"
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path]
        audio_idx, sfx_idx = 1, 2

    cmd.extend(["-i", audio_path])
    
    # 🔥 VIRAL SUBTITLES (Appears at 0.5s after Hero entry)
    clean_text = text.replace("'", "").replace(":", r"\:")
    fontsize = 80 if width == 1080 else 90
    text_end_y = (height / 2) + 300 if width == 1080 else (height / 2) + 250
    text_filter = f"[comp]drawtext=fontfile={FONT_FILE}:text='{clean_text}':fontcolor=#FFE800:fontsize={fontsize}:borderw=4:bordercolor=black:shadowcolor=black@0.8:shadowx=6:shadowy=6:box=1:boxcolor=black@0.5:boxborderw=15:x=(w-text_w)/2:y='max({text_end_y}, h - ((t-0.5)*300))':enable='gt(t,0.5)'[v_out]"
    
    v_filter = base_video_filter + text_filter

    # 🎵 8D SPATIAL AUDIO + SEQUENTIAL SYNC MIXING
    if os.path.exists(sfx_path):
        cmd.extend(["-i", sfx_path])
        # Voice delays slightly to let SFX play first, SFX gets 8D Spatial Pan
        a_filter = f"[{audio_idx}:a]adelay=700|700,volume=1.5[voice];[{sfx_idx}:a]adelay=300|300,volume=0.8,{audio_pan_filter}[sfx];[voice][sfx]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[a_out]"
        cmd.extend(["-filter_complex", f"{v_filter};{a_filter}", "-map", "[v_out]", "-map", "[a_out]"])
    else:
        a_filter = f"[{audio_idx}:a]adelay=500|500,volume=1.5[a_out]"
        cmd.extend(["-filter_complex", f"{v_filter};{a_filter}", "-map", "[v_out]", "-map", "[a_out]"])
        
    cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-t", str(duration + 1.0), "-pix_fmt", "yuv420p", "-preset", "fast", out_path])
    
    print(f"🎬 Rendering Scene {scene_id} [Tracking Face & 8D Audio]...")
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
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-c", "copy", temp_video], check=True)

    final_output = os.path.join(OUTPUT_DIR, "FINAL_AGENCY_MASTERPIECE.mp4")
    
    if os.path.exists(BGM_FILE):
        print("🎵 Adding Cinematic BGM...")
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_video, "-stream_loop", "-1", "-i", BGM_FILE, 
            "-filter_complex", "[1:a]volume=0.3[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]", 
            "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", final_output
        ], check=True)
    else:
        os.rename(temp_video, final_output)
        
    print(f"🎉 BOOM! 8D Spatial Audio + Face Tracking Video Ready: {final_output}")

if __name__ == "__main__":
    main()
