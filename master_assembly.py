import os
import json
import subprocess
import urllib.request
from PIL import Image

# -----------------------------------------------------
# DIRECTORIES & FILES
# -----------------------------------------------------
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

# -----------------------------------------------------
# VIRAL FONT DOWNLOADER
# -----------------------------------------------------
def download_viral_font():
    if not os.path.exists(FONT_FILE):
        print("📥 Downloading Anton Font for Subtitles...")
        urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf", FONT_FILE)

# -----------------------------------------------------
# UTILS
# -----------------------------------------------------
def get_video_dimensions():
    with open(CONFIG_FILE, "r") as f:
        fmt = json.load(f).get("video_format", "long").lower()
        return (1080, 1920) if fmt == "short" else (1920, 1080)

def create_scene_clip(scene_id, scene_data, duration, width, height):
    text = scene_data.get("narration", "")
    anim_style = scene_data.get("animation", "zoom_in") # Fallback to zoom_in
    
    img_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}.jpg")
    audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")
    sfx_path = os.path.join(SFX_DIR, f"sfx_scene_{scene_id}.mp3")
    out_path = os.path.join(OUTPUT_DIR, f"clip_{scene_id}.mp4")
    
    frames = int(duration * 25)
    
    # ==========================================
    # 🔥 1. STORY-DRIVEN CINEMATIC ANIMATIONS (SAFE MODE)
    # ==========================================
    # Yahan sirf smooth panning/zooming hogi (No double head bugs!)
    
    if anim_style == 'slide_left':
        v_filter = f"[0:v]scale={width}:{height},zoompan=z=1.15:d={frames}:x='max(0, iw/2-(iw/zoom/2)-on)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps=25[comp];"
    elif anim_style == 'slide_right':
        v_filter = f"[0:v]scale={width}:{height},zoompan=z=1.15:d={frames}:x='min(iw-(iw/zoom), iw/2-(iw/zoom/2)+on)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps=25[comp];"
    elif anim_style == 'fly_up' or anim_style == 'float_clouds':
        # Y-axis Panning
        v_filter = f"[0:v]scale={width}:{height},zoompan=z=1.15:d={frames}:x='iw/2-(iw/zoom/2)':y='max(0, ih/2-(ih/zoom/2)-on)':s={width}x{height}:fps=25[comp];"
    else: 
        # Default zoom_in (drive_forward isko bhi cover karega)
        v_filter = f"[0:v]scale={width}:{height},zoompan=z='min(zoom+0.0006,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps=25[comp];"

    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-i", audio_path]
    
    # ==========================================
    # 🔥 2. SMOOTH SCROLLING VIRAL SUBTITLES
    # ==========================================
    clean_text = text.replace("'", "").replace(":", r"\:")
    fontsize = 80 if width == 1080 else 90
    text_end_y = (height / 2) + 350 if width == 1080 else (height / 2) + 300
    
    # Text neche se upar (smooth slide up)
    text_filter = f"[comp]drawtext=fontfile={FONT_FILE}:text='{clean_text}':fontcolor=#FFE800:fontsize={fontsize}:borderw=5:bordercolor=black:shadowcolor=black@0.8:shadowx=6:shadowy=6:box=1:boxcolor=black@0.5:boxborderw=15:x=(w-text_w)/2:y='max({text_end_y}, h - (t*250))'[v_out]"
    
    v_filter += text_filter

    # ==========================================
    # 🎵 3. LOUD & CRISP AUDIO MIXING (The Audio Fix)
    # ==========================================
    # Yahan normalize=0 laga hai taaki awaaz dabey (low) na!
    
    if os.path.exists(sfx_path):
        cmd.extend(["-i", sfx_path])
        # Voice = 150% boosted, SFX = 60% with slight delay
        a_filter = f"[1:a]volume=1.5[voice];[2:a]adelay=300|300,volume=0.6[sfx];[voice][sfx]amix=inputs=2:duration=first:normalize=0[a_out]"
        cmd.extend(["-filter_complex", f"{v_filter};{a_filter}", "-map", "[v_out]", "-map", "[a_out]"])
    else:
        # Agar sirf Voiceover hai toh usko bhi boost karenge
        a_filter = f"[1:a]volume=1.5[a_out]"
        cmd.extend(["-filter_complex", f"{v_filter};{a_filter}", "-map", "[v_out]", "-map", "[a_out]"])
        
    cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-t", str(duration), "-pix_fmt", "yuv420p", "-preset", "fast", out_path])
    
    print(f"🎬 Rendering Scene {scene_id} [Animation: {anim_style}]...")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path

# -----------------------------------------------------
# 🚀 MAIN ENGINE
# -----------------------------------------------------
def main():
    download_viral_font()
    
    if not os.path.exists(TIMESTAMPS_FILE): 
        print("❌ Error: Timestamps file missing!")
        return
        
    with open(TIMESTAMPS_FILE, "r") as f: timestamps = json.load(f)
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f: scenes = json.load(f)
    
    width, height = get_video_dimensions()
    clip_list = []
    
    for scene in scenes:
        scene_id = str(scene["scene"])
        duration = timestamps.get(scene_id)
        if duration and os.path.exists(os.path.join(IMAGE_DIR, f"scene_{scene_id}.jpg")):
            clip_list.append(create_scene_clip(scene_id, scene, duration, width, height))
        
    # Concat Text File
    list_txt = os.path.join(OUTPUT_DIR, "concat.txt")
    with open(list_txt, "w") as f:
        for c in clip_list: f.write(f"file '{os.path.abspath(c)}'\n")
            
    temp_video = os.path.join(OUTPUT_DIR, "TEMP_MASTERPIECE.mp4")
    print("🔄 Merging Clips...")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-c", "copy", temp_video], check=True)

    # ==========================================
    # 🎵 AUTO BGM MIXING (Final Polish)
    # ==========================================
    final_output = os.path.join(OUTPUT_DIR, "FINAL_AGENCY_MASTERPIECE.mp4")
    
    if os.path.exists(BGM_FILE):
        print("🎵 Adding Cinematic BGM (Boosted Audio Profile)...")
        # VoiceTrack = 100% (already boosted earlier), BGM = 15% (Loud enough but doesn't overpower voice)
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_video, "-stream_loop", "-1", "-i", BGM_FILE, 
            "-filter_complex", "[1:a]volume=0.15[bgm];[0:a][bgm]amix=inputs=2:duration=first:normalize=0[aout]", 
            "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", final_output
        ], check=True)
    else:
        os.rename(temp_video, final_output)
        
    print(f"🎉 BOOM! Context-Aware Video Ready (Bug-Free & LOUD): {final_output}")

if __name__ == "__main__":
    main()
