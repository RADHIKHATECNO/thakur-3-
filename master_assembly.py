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
FONT_FILE = "Montserrat-Black.ttf"
CASCADE_FILE = "haarcascade_frontalface_default.xml"
BGM_FILE = os.path.join(SFX_DIR, "auto_bgm.mp3")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_assets():
    if not os.path.exists(FONT_FILE):
        try:
            urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Black.ttf", FONT_FILE)
        except:
            urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf", FONT_FILE)
    if not os.path.exists(CASCADE_FILE):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml", CASCADE_FILE)

def get_face_focus_point(image_path):
    try:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = cv2.CascadeClassifier(CASCADE_FILE).detectMultiScale(gray, 1.1, 4)
        if len(faces) > 0:
            x, y, w, h = faces[0]
            cx, cy = x + (w / 2), y + (h / 2)
            return f"x='{cx}-(iw/zoom/2)':y='{cy}-(ih/zoom/2)'"
    except: pass
    return "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"

def create_parallax_layers(scene_id):
    img_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}.jpg")
    fg_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}_fg.png")
    if os.path.exists(img_path) and not os.path.exists(fg_path):
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
            return bbox and ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) > (img.width * img.height * 0.05))
    except: return False

def get_video_config():
    with open(CONFIG_FILE, "r") as f:
        data = json.load(f)
        fmt = data.get("video_format", "long").lower()
        # 🔥 FIX: Yahan return variables properly unpack honge ab!
        width, height = (1080, 1920) if fmt == "short" else (1920, 1080)
        client_name = data.get("client_name", "@AgencyVideo")
        return width, height, client_name

def generate_karaoke_text(text, duration, width, height, client_name):
    words = text.replace("'", "").replace(":", r"\:").split()
    filters = []
    chunk_size = 2 if width == 1080 else 4
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    time_per_chunk = duration / max(1, len(chunks))
    
    fontsize = 65 if width == 1080 else 85
    y_pos = (height / 2) + 350 if width == 1080 else (height / 2) + 300
    colors = ["#00FFFF", "#FFE800", "#FFFFFF"] 
    
    for i, chunk in enumerate(chunks):
        st = i * time_per_chunk
        et = (i + 1) * time_per_chunk if i < len(chunks)-1 else duration + 1.0
        c = colors[i % len(colors)]
        filters.append(f"drawtext=fontfile={FONT_FILE}:text='{chunk}':fontcolor={c}:fontsize={fontsize}:borderw=5:bordercolor=black:shadowcolor=black@0.9:shadowx=4:shadowy=4:box=1:boxcolor=black@0.5:boxborderw=10:x=(w-text_w)/2:y={y_pos}:enable='between(t,{st},{et})'")
        
    wm_size = 40 if width == 1080 else 55
    filters.append(f"drawtext=fontfile={FONT_FILE}:text='{client_name}':fontcolor=white@0.4:fontsize={wm_size}:x=w-text_w-30:y=30")
    return ",".join(filters)

def create_scene_clip(scene_id, scene_data, duration, width, height, client_name):
    text = scene_data.get("narration", "")
    cam = scene_data.get("camera", "smooth_pan") 
    vfx = scene_data.get("vfx_effect", "none")
    
    img_path, fg_path = create_parallax_layers(scene_id)
    audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")
    sfx_path = os.path.join(SFX_DIR, f"sfx_scene_{scene_id}.mp3")
    out_path = os.path.join(OUTPUT_DIR, f"clip_{scene_id}.mp4")
    
    frames = int((duration + 1.0) * 25)
    has_char = has_valid_character(fg_path)
    focus = get_face_focus_point(img_path)
    
    # EXACT 9:16 CROP
    crop_scale = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}:(iw-ow)/2:(ih-oh)/2"
    
    # 🎥 CAMERA LOGIC (Face Tracking + Shake/Zoom)
    if cam == 'shake':
        bg_cam = f"scale=iw*1.1:ih*1.1,crop={width}:{height}:'(iw-ow)/2+15*sin(t*15)':'(ih-oh)/2+15*cos(t*15)'"
        fg_cam = f"scale=iw*1.1:ih*1.1,crop={width}:{height}:'(iw-ow)/2+25*sin(t*15)':'(ih-oh)/2+25*cos(t*15)'"
    elif cam == 'fast_zoom':
        bg_cam = f"zoompan=z='min(zoom+0.015,1.5)':d={frames}:{focus}:s={width}x{height}:fps=25"
        fg_cam = f"zoompan=z='min(zoom+0.015,1.5)':d={frames}:{focus}:s={width}x{height}:fps=25"
    elif cam == 'zoom_out':
        bg_cam = f"zoompan=z='max(1.3-(0.005*on),1.0)':d={frames}:{focus}:s={width}x{height}:fps=25"
        fg_cam = ""
    else: # smooth_pan
        bg_cam = f"zoompan=z='min(zoom+0.0005,1.15)':d={frames}:{focus}:s={width}x{height}:fps=25"
        fg_cam = ""

    # ✨ VFX LOGIC
    vfx_filter = ",fade=t=in:st=0:d=0.2:color=white" if vfx == 'white_flash' else ""

    # 🎬 COMPOSITING
    if has_char:
        bg_filter = f"[0:v]{crop_scale},gblur=sigma=8,{bg_cam}{vfx_filter}[bg];"
        if fg_cam:
            fg_filter = f"[1:v]{crop_scale},{fg_cam},format=rgba[fg];[bg][fg]overlay=0:0[comp];"
        else:
            fg_filter = f"[1:v]{crop_scale},format=rgba[fg];[bg][fg]overlay=0:0[comp];"
        
        v_filter_base = bg_filter + fg_filter
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-loop", "1", "-i", fg_path]
        a_idx, sfx_idx = 2, 3
    else:
        v_filter_base = f"[0:v]{crop_scale},{bg_cam}{vfx_filter}[comp];"
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path]
        a_idx, sfx_idx = 1, 2

    cmd.extend(["-i", audio_path])
    v_filter = v_filter_base + f"[comp]{generate_karaoke_text(text, duration, width, height, client_name)}[v_out]"

    # 🔊 LOUD 8D AUDIO SYNC
    if os.path.exists(sfx_path):
        cmd.extend(["-i", sfx_path])
        sfx_delay = scene_data.get("sfx_delay_ms", 300)
        a_filter = f"[{a_idx}:a]volume=1.5[voice];[{sfx_idx}:a]adelay={sfx_delay}|{sfx_delay},volume=1.0[sfx];[voice][sfx]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a_out]"
        cmd.extend(["-filter_complex", f"{v_filter};{a_filter}", "-map", "[v_out]", "-map", "[a_out]"])
    else:
        a_filter = f"[{a_idx}:a]volume=1.5[a_out]"
        cmd.extend(["-filter_complex", f"{v_filter};{a_filter}", "-map", "[v_out]", "-map", "[a_out]"])
        
    cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", "-t", str(duration), "-pix_fmt", "yuv420p", "-preset", "fast", out_path])
    
    print(f"🎬 Editing Scene {scene_id} [Parallax: {has_char} | Camera: {cam.upper()} | VFX: {vfx.upper()}]...")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path

def main():
    download_assets()
    if not os.path.exists(TIMESTAMPS_FILE): return
        
    with open(TIMESTAMPS_FILE, "r") as f: timestamps = json.load(f)
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f: scenes = json.load(f)
    
    width, height, client_name = get_video_config()
    clip_list = []
    
    for scene in scenes:
        scene_id = str(scene["scene"])
        duration = timestamps.get(scene_id)
        if duration and os.path.exists(os.path.join(IMAGE_DIR, f"scene_{scene_id}.jpg")):
            clip_list.append(create_scene_clip(scene_id, scene, duration, width, height, client_name))
        
    list_txt = os.path.join(OUTPUT_DIR, "concat.txt")
    with open(list_txt, "w") as f:
        for c in clip_list: f.write(f"file '{os.path.abspath(c)}'\n")
            
    temp_video = os.path.join(OUTPUT_DIR, "TEMP_MASTERPIECE.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-c:v", "copy", "-c:a", "aac", "-ar", "44100", "-ac", "2", temp_video], check=True)

    final_output = os.path.join(OUTPUT_DIR, "FINAL_AGENCY_MASTERPIECE.mp4")
    if os.path.exists(BGM_FILE):
        print("🎵 Adding Cinematic BGM...")
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_video, "-stream_loop", "-1", "-i", BGM_FILE, 
            "-filter_complex", "[1:a]volume=0.25[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]", 
            "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", final_output
        ], check=True)
    else:
        os.rename(temp_video, final_output)
        
    print(f"🎉 BOOM! God-Mode Video Ready: {final_output}")

if __name__ == "__main__":
    main()
