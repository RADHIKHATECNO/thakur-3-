import os
import sys
import json
import subprocess
import urllib.request

IMAGE_DIR = "scene_images"
OUTPUT_DIR = "final_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

VOICE_FILE = "voiceover.mp3"
TIMESTAMPS_FILE = "audio_timestamps.json"
BGM_FILE = "bgm.wav"
FONT_FILE = "Roboto-Bold.ttf"
CHANNEL_NAME = "@THAKURSAHAB" 

def download_font():
    if not os.path.exists(FONT_FILE):
        print("📥 Downloading Font for Watermark...")
        font_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
        try:
            urllib.request.urlretrieve(font_url, FONT_FILE)
        except Exception as e:
            print(f"⚠️ Font download failed: {e}")

def create_video_from_image(img_path, duration, index):
    """Magic function: Converts a static image into a Ken Burns (Zoom) video clip exactly matching the audio length"""
    out_path = os.path.join(OUTPUT_DIR, f"temp_clip_{index}.mp4")
    
    # 25 fps x duration = total frames
    frames = int(duration * 25)
    
    # Ken Burns Zoom-In Effect (Smooth cinematic zoom)
    # Scale exactly to 1920x1080
    vf = f"zoompan=z='min(zoom+0.0005,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080,framerate=25"
    
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", img_path,
        "-vf", vf, "-c:v", "libx264", "-t", str(duration),
        "-pix_fmt", "yuv420p", "-preset", "fast", out_path
    ]
    
    print(f"⚙️ Animating Image {index} for {duration} seconds...")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path

def main():
    download_font()
    
    if not os.path.exists(TIMESTAMPS_FILE):
        print("❌ audio_timestamps.json missing! Cannot sync.")
        sys.exit(1)
        
    with open(TIMESTAMPS_FILE, "r") as f:
        timestamps = json.load(f)
        
    print("🎬 Phase 1: Converting Static Images to Animated Clips (Ken Burns Effect)...")
    clip_list = []
    
    # Generate animated clips based on EXACT voiceover timings
    for idx_str, duration in timestamps.items():
        img_path = os.path.join(IMAGE_DIR, f"scene_{idx_str}.jpg")
        
        # Fallback if image failed to generate
        if not os.path.exists(img_path):
            print(f"⚠️ Scene {idx_str} image missing, using previous image as fallback...")
            img_path = os.path.join(IMAGE_DIR, f"scene_{int(idx_str)-1}.jpg")
            if not os.path.exists(img_path):
                continue
                
        clip_path = create_video_from_image(img_path, duration, idx_str)
        clip_list.append(clip_path)

    # Concat all silent animated clips
    list_txt_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(list_txt_path, "w") as f:
        for clip in clip_list:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    silent_video = os.path.join(OUTPUT_DIR, "silent_video.mp4")
    print("🎬 Phase 2: Merging animated clips together...")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt_path, "-c", "copy", silent_video], check=True)

    print("🎵 Phase 3: Mixing Voiceover, AI BGM Loop, and Watermark...")
    final_output = os.path.join(OUTPUT_DIR, "Final_Masterpiece.mp4")
    
    # Watermark text setup
    drawtext = f"drawtext=fontfile={FONT_FILE}:text='{CHANNEL_NAME}':fontcolor=white@0.4:fontsize=45:x=(w-text_w)-30:y=30" if os.path.exists(FONT_FILE) else ""

    if os.path.exists(BGM_FILE) and os.path.exists(VOICE_FILE):
        # We loop the BGM infinitely, mix it at 8% volume, voice at 150% volume.
        # -shortest cuts the looped bgm right when the video/voiceover ends.
        filter_complex = f"[1:a]volume=1.5[voice];[2:a]volume=0.08[bgm];[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", silent_video,
            "-i", VOICE_FILE,
            "-stream_loop", "-1", "-i", BGM_FILE, # Infinite loop for BGM
            "-filter_complex", filter_complex,
            "-map", "0:v", "-map", "[aout]",
            "-vf", drawtext if drawtext else "copy",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "320k",
            "-shortest", final_output
        ]
        subprocess.run(cmd, check=True)
    else:
        # If no BGM, just mix Voiceover
        cmd = [
            "ffmpeg", "-y", "-i", silent_video, "-i", VOICE_FILE,
            "-map", "0:v", "-map", "1:a",
            "-vf", drawtext if drawtext else "copy",
            "-c:v", "libx264", "-c:a", "aac", "-shortest", final_output
        ]
        subprocess.run(cmd, check=True)

    print("🎉 MASTERPIECE GENERATED SUCCESSFULLY: Final_Masterpiece.mp4")

if __name__ == "__main__":
    main()
