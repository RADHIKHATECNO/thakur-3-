import os
import sys
import json
import subprocess

IMAGE_DIR = "scene_images"
AUDIO_DIR = "audio_clips"
OUTPUT_DIR = "final_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TIMESTAMPS_FILE = "audio_timestamps.json"
BGM_FILE = "bgm.wav"

def create_animated_clip(img_path, audio_path, duration, index):
    out_path = os.path.join(OUTPUT_DIR, f"clip_{index}.mp4")
    frames = int(duration * 25)
    
    # Smooth Ken Burns Zoom In Effect
    vf = f"zoompan=z='min(zoom+0.0005,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080,framerate=25"
    
    cmd = [
        "ffmpeg", "-y", 
        "-loop", "1", "-i", img_path, 
        "-i", audio_path,
        "-vf", vf, 
        "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration), "-pix_fmt", "yuv420p", "-preset", "fast", out_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path

def main():
    with open(TIMESTAMPS_FILE, "r") as f:
        timestamps = json.load(f)
        
    print("🎬 Rendering Animated Video Clips with Perfect Audio Sync...")
    clip_list = []
    
    for idx_str, duration in timestamps.items():
        img_path = os.path.join(IMAGE_DIR, f"scene_{idx_str}.jpg")
        audio_path = os.path.join(AUDIO_DIR, f"line_{idx_str}.mp3")
        
        if not os.path.exists(img_path):
            img_path = os.path.join(IMAGE_DIR, f"scene_{int(idx_str)-1}.jpg") # Fallback
            
        if os.path.exists(img_path) and os.path.exists(audio_path):
            clip = create_animated_clip(img_path, audio_path, duration, idx_str)
            clip_list.append(clip)
            print(f"✅ Rendered Clip {idx_str} ({duration}s)")

    # Combine all clips
    list_txt = os.path.join(OUTPUT_DIR, "concat.txt")
    with open(list_txt, "w") as f:
        for c in clip_list: f.write(f"file '{os.path.abspath(c)}'\n")
        
    temp_video = os.path.join(OUTPUT_DIR, "temp_video.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-c", "copy", temp_video], check=True)

    print("🎵 Adding AI Background Music (Auto-Looped)...")
    final_output = os.path.join(OUTPUT_DIR, "Final_Masterpiece.mp4")
    
    if os.path.exists(BGM_FILE):
        # Mix BGM at 8% volume, auto loop BGM till video ends
        filter_complex = "[1:a]volume=0.08[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]"
        cmd = [
            "ffmpeg", "-y", 
            "-i", temp_video, 
            "-stream_loop", "-1", "-i", BGM_FILE, 
            "-filter_complex", filter_complex, 
            "-map", "0:v", "-map", "[aout]", 
            "-c:v", "copy", "-c:a", "aac", "-shortest", final_output
        ]
        subprocess.run(cmd, check=True)
    else:
        os.rename(temp_video, final_output)
        
    print("🎉 BOOM! Final Video Rendered: Final_Masterpiece.mp4")

if __name__ == "__main__":
    main()
