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
BGM_FILE = os.path.join(SFX_DIR, "auto_bgm.mp3")
FONT_FILE = "Montserrat-Black.ttf"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_assets():
    if not os.path.exists(FONT_FILE):
        print("📥 Downloading Premium Montserrat Font...")
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Black.ttf"
            urllib.request.urlretrieve(url, FONT_FILE)
        except:
            urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf", FONT_FILE)

def get_video_dimensions():
    with open(CONFIG_FILE, "r") as f:
        return (1080, 1920) if json.load(f).get("video_format", "long").lower() == "short" else (1920, 1080)

def create_parallax_layers(img_path, scene_id):
    fg_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}_fg.png")
    if not os.path.exists(fg_path):
        try:
            print(f"✂️ AI Cutting foreground for Scene {scene_id}...")
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

def generate_karaoke_text_filters(text, duration, width, height):
    words = text.replace("'", "").replace(":", r"\:").split()
    filters = []
    chunk_size = max(1, len(words) // 3)
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    
    time_per_chunk = duration / max(1, len(chunks))
    fontsize = 70 if width == 1080 else 85
    y_pos = (height / 2) + 350 if width == 1080 else (height / 2) + 300
    colors = ["#00FFFF", "#FFE800", "#FFFFFF"] 
    
    for i, chunk in enumerate(chunks):
        start_time = i * time_per_chunk
        color = colors[i % len(colors)]
        f = f"drawtext=fontfile={FONT_FILE}:text='{chunk}':fontcolor={color}:fontsize={fontsize}:borderw=5:bordercolor=black:shadowcolor=black@0.9:shadowx=5:shadowy=5:box=1:boxcolor=black@0.4:boxborderw=10:x=(w-text_w)/2:y={y_pos}:enable='between(t,{start_time},100)'"
        filters.append(f)
    return ",".join(filters)

def create_scene_clip(scene_id, scene_data, duration, width, height):
    text = scene_data.get("narration", "")
    camera_move = scene_data.get("camera", "smooth_pan") 
    
    img_path, fg_path = create_parallax_layers(os.path.join(IMAGE_DIR, f"scene_{scene_id}.jpg"), scene_id)
    audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")
    sfx_path = os.path.join(SFX_DIR, f"sfx_scene_{scene_id}.mp3")
    out_path = os.path.join(OUTPUT_DIR, f"clip_{scene_id}.mp4")
    
    frames = int(duration * 25)
    has_char = has_valid_character(fg_path)
    
    # 🔥 FIX: PERFECT 9:16 CROP MATH
    scale_crop = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    
    if has_char:
        # 🔥 THE ULTIMATE COMBO: PARALLAX + AI CAMERA!
        if camera_move == 'shake':
            bg_filter = f"[0:v]{scale_crop},scale=iw*1.1:ih*1.1,gblur=sigma=8,crop={width}:{height}:'(iw-ow)/2+15*sin(t*15)':'(ih-oh)/2+15*cos(t*15)'[bg];"
            fg_filter = f"[1:v]{scale_crop},scale=iw*1.1:ih*1.1,format=rgba,crop={width}:{height}:'(iw-ow)/2+25*sin(t*15)':'(ih-oh)/2+25*cos(t*15)'[fg];[bg][fg]overlay=0:0[comp];"
        elif camera_move == 'zoom_out':
            bg_filter = f"[0:v]{scale_crop},gblur=sigma=8,zoompan=z='max(1.5-(0.005*on),1.0)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps=25[bg];"
            fg_filter = f"[1:v]{scale_crop},format=rgba[fg];[bg][fg]overlay=0:0[comp];"
        elif camera_move == 'fast_zoom':
            bg_filter = f"[0:v]{scale_crop},gblur=sigma=8,zoompan=z='min(zoom+0.015,1.5)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps=25[bg];"
            fg_filter = f"[1:v]{scale_crop},format=rgba,zoompan=z='min(zoom+0.015,1.5)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps=25[fg];[bg][fg]overlay=0:0[comp];"
        else: # smooth_pan
            bg_filter = f"[0:v]{scale_crop},gblur=sigma=8,zoompan=z='min(zoom+0.0005,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps=25[bg];"
            fg_filter = f"[1:v]{scale_crop},format=rgba[fg];[bg][fg]overlay=0:0[comp];"
            
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-loop", "1", "-i", fg_path, "-i", audio_path]
        audio_idx, sfx_idx = 2, 3
    else:
        # Fallback Scenery (No Character)
        if camera_move == 'shake':
            v_filter_base = f"[0:v]{scale_crop},scale=iw*1.1:ih*1.1,crop={width}:{height}:'(iw-ow)/2+15*sin(t*15)':'(ih-oh)/2+15*cos(t*15)'[comp];"
        elif camera_move == 'zoom_out':
            v_filter_base = f"[0:v]{scale_crop},zoompan=z='max(1.5-(0.005*on),1.0)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps=25[comp];"
        elif camera_move == 'fast_zoom':
            v_filter_base = f"[0:v]{scale_crop},zoompan=z='min(zoom+0.015,1.5)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps=25[comp];"
        else:
            v_filter_base = f"[0:v]{scale_crop},zoompan=z='min(zoom+0.0005,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps=25[comp];"
            
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-i", audio_path]
        audio_idx, sfx_idx = 1, 2

    # 📝 ADD KARAOKE TEXT
    text_filters = generate_karaoke_text_filters(text, duration, width, height)
    
    if has_char:
        v_filter = bg_filter + fg_filter + f"[comp]{text_filters}[v_out]"
    else:
        v_filter = v_filter_base + f"[comp]{text_filters}[v_out]"

    # 🔊 LOUD AUDIO MIXING
    if os.path.exists(sfx_path):
        cmd.extend(["-i", sfx_path])
        a_filter = f"[{audio_idx}:a]volume=1.5[voice];[{sfx_idx}:a]adelay=100|100,volume=0.8[sfx];[voice][sfx]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[a_out]"
        cmd.extend(["-filter_complex", f"{v_filter};{a_filter}", "-map", "[v_out]", "-map", "[a_out]"])
    else:
        a_filter = f"[{audio_idx}:a]volume=1.5[a_out]"
        cmd.extend(["-filter_complex", f"{v_filter};{a_filter}", "-map", "[v_out]", "-map", "[a_out]"])
        
    cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", "-t", str(duration), "-pix_fmt", "yuv420p", "-preset", "fast", out_path])
    
    print(f"🎬 Rendering Scene {scene_id} [Parallax: {has_char} | Camera: {camera_move.upper()}]...")
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
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_video, "-stream_loop", "-1", "-i", BGM_FILE, 
            "-filter_complex", "[1:a]volume=0.4[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]", 
            "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", final_output
        ], check=True)
    else:
        os.rename(temp_video, final_output)
        
    print(f"🎉 BOOM! Cinematic Camera + Parallax + Karaoke Text Ready: {final_output}")

if __name__ == "__main__":
    main()
