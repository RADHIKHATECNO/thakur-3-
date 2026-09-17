import os
import subprocess
import re
import urllib.request

INPUT_DIR = "generated_videos"
OUTPUT_DIR = "final_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CHANNEL_NAME = "@THAKURSAHAB" 
FONT_FILE = "Roboto-Bold.ttf"

def download_font():
    if not os.path.exists(FONT_FILE):
        print("📥 Downloading Font for Watermark...")
        font_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
        try:
            urllib.request.urlretrieve(font_url, FONT_FILE)
            print("✅ Font downloaded successfully!")
        except Exception as e:
            print(f"⚠️ Font download failed: {e}")

def process_smooth_fade(v_path, index):
    out_path = os.path.join(OUTPUT_DIR, f"clip_{index}.mp4")
    fade_dur = 0.5
    
    if os.path.exists(FONT_FILE):
        drawtext = f",drawtext=fontfile={FONT_FILE}:text='{CHANNEL_NAME}':fontcolor=white@0.5:fontsize=50:x=(w-text_w)/2:y=100"
    else:
        drawtext = "" 

    vf = f"scale=1080:1920:flags=lanczos:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,format=yuv420p,fade=t=in:st=0:d={fade_dur},fade=t=out:st=4.5:d={fade_dur}{drawtext}"
    af = f"volume=3.0,afade=t=in:st=0:d={fade_dur},afade=t=out:st=4.5:d={fade_dur}"
    
    cmd = [
        "ffmpeg", "-y", "-i", v_path, "-vf", vf, "-af", af,
        "-c:v", "libx264", "-crf", "23", "-preset", "veryfast", "-c:a", "aac", "-b:a", "320k", out_path
    ]
    print(f"⚙️ Rendering clip {index} with Watermark...")
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return out_path

def main():
    video_files = [f for f in os.listdir(INPUT_DIR) if f.startswith("video_") and f.endswith(".mp4")]
    if not video_files:
        print("❌ No videos found to merge!")
        return

    download_font()
    video_files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
    processed_clips = []
    
    print("✂️ Processing AI Clips with Fades & Watermarks...")
    for v_name in video_files:
        v_path = os.path.join(INPUT_DIR, v_name)
        idx = int(re.search(r'\d+', v_name).group())
        processed_clips.append(process_smooth_fade(v_path, idx))

    list_path = "list.txt"
    with open(list_path, "w") as f:
        for clip in processed_clips: 
            f.write(f"file '{clip}'\n")

        if os.path.exists("outro.mp4"):
            print("⚙️ Formatting Human Outro to match AI Video Size...")
            outro_out = os.path.join(OUTPUT_DIR, "processed_outro.mp4")
            vf_outro = "scale=1080:1920:flags=lanczos:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,format=yuv420p"
            subprocess.run([
                "ffmpeg", "-y", "-i", "outro.mp4", "-vf", vf_outro,
                "-c:v", "libx264", "-crf", "23", "-preset", "veryfast", "-c:a", "aac", "-b:a", "320k", outro_out
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            f.write(f"file '{outro_out}'\n")
            print("✅ Outro added to merge list!")

    temp_output = os.path.join(OUTPUT_DIR, "temp_master.mp4")
    print("🎬 Merging all clips into Temporary Master...")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", temp_output], check=True)

    final_output = os.path.join(OUTPUT_DIR, "Final_4K_Monetizable_Short.mp4")

    # 👇 BGM MIXING LOGIC (With 60% Volume & Boost Fix) 👇
    if os.path.exists("bgm.wav"):
        print("🎵 AI BGM Detected! Mixing Music (60%) with Video Foley (100%)...")
        cmd = [
            "ffmpeg", "-y", 
            "-i", temp_output, 
            "-stream_loop", "-1", "-i", "bgm.wav", 
            # Yahan maine volume 0.60 kiya hai, aur mix hone ke baad [mix]volume=2.0 lagaya hai taaki aawaz dabe nahi!
            "-filter_complex", "[0:a]volume=1.0[a1];[1:a]volume=3.5[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[mix];[mix]volume=2.0[a]", 
            "-map", "0:v", "-map", "[a]", 
            "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", final_output
        ]
        subprocess.run(cmd, check=True)
        print("🎉 MASTERPIECE WITH 100% ORIGINAL AI BGM GENERATED!")
    else:
        os.rename(temp_output, final_output)
        print("🎉 MASTERPIECE (No BGM) GENERATED SUCCESSFULLY!")

if __name__ == "__main__": 
    main()
