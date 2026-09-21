import os
import json
import subprocess

IMAGE_DIR = "scene_images"
AUDIO_DIR = "audio_clips"
SFX_DIR = "sfx_clips"
OUTPUT_DIR = "final_output"
SCRIPT_FILE = "script_data.json"
TIMESTAMPS_FILE = "audio_timestamps.json"
CONFIG_FILE = "client_setup.json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_video_dimensions():
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
        fmt = config.get("video_format", "long").lower()
        if fmt == "short":
            return 1080, 1920
        return 1920, 1080

def create_scene_clip(scene_id, text, duration, width, height):
    img_path = os.path.join(IMAGE_DIR, f"scene_{scene_id}.jpg")
    audio_path = os.path.join(AUDIO_DIR, f"scene_{scene_id}.mp3")
    sfx_path = os.path.join(SFX_DIR, f"sfx_scene_{scene_id}.mp3")
    out_path = os.path.join(OUTPUT_DIR, f"clip_{scene_id}.mp4")
    
    # 25 fps video
    frames = int(duration * 25)
    
    # 1. Ken Burns Effect (Parallax Zoom-in)
    zoom_filter = f"zoompan=z='min(zoom+0.0008,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height},framerate=25"
    
    # 2. Text Subtitles (Center, Yellow, Bold)
    # Note: For GitHub actions, ensure fonts are available or use default.
    clean_text = text.replace("'", "").replace(":", "")
    fontsize = 60 if width == 1080 else 75
    text_filter = f"drawtext=text='{clean_text}':fontcolor=yellow:fontsize={fontsize}:x=(w-text_w)/2:y=(h-text_h)/2+300:borderw=4:bordercolor=black"
    
    # Visual Filter combine
    v_filter = f"{zoom_filter},{text_filter}"
    
    # Audio Setup (Voiceover + SFX mix if SFX exists)
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-i", audio_path]
    
    if os.path.exists(sfx_path):
        cmd.extend(["-i", sfx_path])
        # Mix Voice (loud) and SFX (medium volume)
        filter_complex = "[1:a]volume=1.2[voice];[2:a]volume=0.4[sfx];[voice][sfx]amix=inputs=2:duration=first[aout]"
        cmd.extend(["-filter_complex", filter_complex, "-map", "0:v", "-map", "[aout]"])
    else:
        cmd.extend(["-map", "0:v", "-map", "1:a"])
        
    cmd.extend([
        "-vf", v_filter, 
        "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration), "-pix_fmt", "yuv420p", "-preset", "fast", out_path
    ])
    
    print(f"⚙️ Rendering Scene {scene_id} with Subtitles and Parallax...")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path

def main():
    if not os.path.exists(TIMESTAMPS_FILE):
        print("❌ ERROR: Timestamps missing!")
        return
        
    with open(TIMESTAMPS_FILE, "r") as f:
        timestamps = json.load(f)
        
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        scenes = {str(s["scene"]): s["narration"] for s in json.load(f)}
        
    width, height = get_video_dimensions()
    
    clip_list = []
    
    # Render Individual Clips
    for scene_id, duration in timestamps.items():
        text = scenes.get(scene_id, "")
        clip = create_scene_clip(scene_id, text, duration, width, height)
        clip_list.append(clip)
        print(f"✅ Rendered Scene {scene_id} ({duration}s)")
        
    # Final Merge
    list_txt = os.path.join(OUTPUT_DIR, "concat.txt")
    with open(list_txt, "w") as f:
        for c in clip_list: 
            f.write(f"file '{os.path.abspath(c)}'\n")
            
    final_output = os.path.join(OUTPUT_DIR, "FINAL_MASTERPIECE.mp4")
    print("🎬 Merging all scenes into Final Masterpiece...")
    
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-c", "copy", final_output], check=True)
    
    print(f"🎉 BOOM! Video is Ready: {final_output}")

if __name__ == "__main__":
    main()
