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
        print("📥 Downloading Font...")
        try:
            urllib.request.urlretrieve(
                "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
                FONT_FILE
            )
            print("✅ Font downloaded!")
        except Exception as e:
            print(f"⚠️ Font download failed: {e}")

def process_clip(v_path, index):
    """Process each clip: 16:9 format + watermark (NO fade, seamless join)"""
    out_path = os.path.join(OUTPUT_DIR, f"clip_{index}.mp4")
    
    # Watermark
    if os.path.exists(FONT_FILE):
        drawtext = f",drawtext=fontfile={FONT_FILE}:text='{CHANNEL_NAME}':fontcolor=white@0.4:fontsize=40:x=(w-text_w)-20:y=20"
    else:
        drawtext = ""

    # 🔴 16:9 ASPECT RATIO for YouTube Long Videos (1920x1080)
    # 🔴 NO FADE EFFECTS - Clean clip for seamless crossfade later
    vf = f"scale=1920:1080:flags=lanczos:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30,format=yuv420p{drawtext}"
    af = "volume=3.0"  # No audio fade
    
    cmd = [
        "ffmpeg", "-y", "-i", v_path,
        "-vf", vf,
        "-af", af,
        "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "320k",
        out_path
    ]
    
    print(f"⚙️ Processing clip {index} (16:9, seamless)...")
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return out_path

def main():
    video_files = [f for f in os.listdir(INPUT_DIR) if f.startswith("video_") and f.endswith(".mp4")]
    
    if not video_files:
        print("❌ No videos found!")
        return

    download_font()
    video_files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
    processed_clips = []

    print("✂️ Processing AI clips (16:9 format, no fades)...")
    for v_name in video_files:
        v_path = os.path.join(INPUT_DIR, v_name)
        idx = int(re.search(r'\d+', v_name).group())
        processed_clips.append(process_clip(v_path, idx))

    # 🔴 SEAMLESS CROSSFADE MERGE (instead of concat)
    # Using xfade filter for smooth transitions between clips
    
    if len(processed_clips) == 1:
        # Only one clip, just copy
        temp_output = processed_clips[0]
    else:
        print("🎬 Merging clips with SEAMLESS CROSSFADE transitions...")
        
        # Build complex xfade filter chain
        # xfade creates a smooth dissolve transition between clips
        filter_complex = ""
        inputs = ""
        
        for i, clip in enumerate(processed_clips):
            inputs += f"-i {clip} "
        
        # Calculate transition points (0.3 sec crossfade between each clip)
        # Each clip is 5 sec, transition at 4.7 sec
        offset = 0
        transition_dur = 0.3
        
        if len(processed_clips) == 2:
            filter_complex = f"[0:v][1:v]xfade=transition=dissolve:duration={transition_dur}:offset=4.7[v]"
            audio_mix = "[0:a][1:a]concat=n=2:v=0:a=1[a]"
        else:
            # Chain multiple xfades
            for i in range(len(processed_clips) - 1):
                if i == 0:
                    filter_complex += f"[0:v][1:v]xfade=transition=dissolve:duration={transition_dur}:offset={offset + 4.7}[v{i}];"
                elif i == len(processed_clips) - 2:
                    filter_complex += f"[v{i-1}][{i+1}:v]xfade=transition=dissolve:duration={transition_dur}:offset={offset + 4.7}[v]"
                else:
                    filter_complex += f"[v{i-1}][{i+1}:v]xfade=transition=dissolve:duration={transition_dur}:offset={offset + 4.7}[v{i}];"
                offset += 4.7
            
            # Audio concat
            audio_inputs = "".join([f"[{i}:a]" for i in range(len(processed_clips))])
            audio_mix = f"{audio_inputs}concat=n={len(processed_clips)}:v=0:a=1[a]"
        
        temp_output = os.path.join(OUTPUT_DIR, "temp_merged.mp4")
        
        merge_cmd = f"ffmpeg -y {inputs} -filter_complex \"{filter_complex};{audio_mix}\" -map \"[v]\" -map \"[a]\" -c:v libx264 -crf 23 -preset veryfast -c:a aac -b:a 320k {temp_output}"
        
        subprocess.run(merge_cmd, shell=True, check=True)

    # Add outro if exists
    if os.path.exists("outro.mp4"):
        print("⚙️ Adding outro (16:9 format)...")
        outro_formatted = os.path.join(OUTPUT_DIR, "outro_16x9.mp4")
        
        subprocess.run([
            "ffmpeg", "-y", "-i", "outro.mp4",
            "-vf", "scale=1920:1080:flags=lanczos:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30,format=yuv420p",
            "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "320k",
            outro_formatted
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Crossfade with outro
        with_outro = os.path.join(OUTPUT_DIR, "temp_with_outro.mp4")
        
        subprocess.run([
            "ffmpeg", "-y",
            "-i", temp_output,
            "-i", outro_formatted,
            "-filter_complex",
            f"[0:v][1:v]xfade=transition=dissolve:duration=0.5:offset={len(processed_clips)*4.7}[v];[0:a][1:a]concat=n=2:v=0:a=1[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "320k",
            with_outro
        ], check=True)
        
        temp_output = with_outro

    final_output = os.path.join(OUTPUT_DIR, "Final_4K_Monetizable_Long_Video.mp4")

    # Mix BGM if exists
    if os.path.exists("bgm.wav"):
        print("🎵 Mixing AI BGM with video audio...")
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_output,
            "-stream_loop", "-1", "-i", "bgm.wav",
            "-filter_complex",
            "[0:a]volume=1.2[a1];[1:a]volume=0.4[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[mix];[mix]volume=2.0[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "320k",
            final_output
        ]
        subprocess.run(cmd, check=True)
        print("🎉 MASTERPIECE WITH BGM READY!")
    else:
        os.rename(temp_output, final_output)
        print("🎉 MASTERPIECE READY (No BGM)!")

if __name__ == "__main__":
    main()
