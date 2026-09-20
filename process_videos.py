import os
import subprocess
import re

INPUT_DIR = "generated_videos"
AUDIO_DIR = "scene_audio"
OUTPUT_DIR = "final_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CHANNEL_NAME = "@YourChannel"
FONT_FILE = "Roboto-Bold.ttf"

def download_font():
    import urllib.request
    if not os.path.exists(FONT_FILE):
        try:
            urllib.request.urlretrieve(
                "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
                FONT_FILE
            )
            print("✅ Font downloaded!")
        except:
            print("⚠️ Font download failed. Watermark skipped.")

def get_audio_duration(audio_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())
    except:
        return 5.0

def process_clip(v_path, idx, format_type):
    voice_path = os.path.join(AUDIO_DIR, f"voice_{idx}.mp3")
    out_path = os.path.join(OUTPUT_DIR, f"clip_{idx}.mp4")

    # Format के हिसाब से Resolution
    if format_type == "SHORT":
        scale = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    else:
        scale = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"

    # Professional Zoom Effect (Fade की जगह)
    zoom_effect = "zoompan=z='min(zoom+0.0008,1.05)':d=125:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',fps=30"

    # Watermark
    if os.path.exists(FONT_FILE):
        watermark = f",drawtext=fontfile={FONT_FILE}:text='{CHANNEL_NAME}':fontcolor=white@0.6:fontsize=45:x=(w-text_w)/2:y=80:shadowcolor=black@0.8:shadowx=2:shadowy=2"
    else:
        watermark = ""

    vf = f"{scale},setsar=1,format=yuv420p,{zoom_effect}{watermark}"

    if os.path.exists(voice_path):
        duration = get_audio_duration(voice_path)
        print(f"🎬 Clip {idx}: Voice duration = {duration:.1f}s")
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", v_path,
            "-i", voice_path,
            "-vf", vf,
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(duration),  # Voice ke hisaab se clip kato
            out_path
        ]
    else:
        print(f"⚠️ No voice for clip {idx}. Using 5s default.")
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", v_path,
            "-vf", vf,
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-an",
            "-t", "5",
            out_path
        ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return out_path
    except Exception as e:
        print(f"❌ Clip {idx} failed: {e}")
        return None

def main():
    download_font()

    format_type = "SHORT"
    if os.path.exists("video_format.txt"):
        with open("video_format.txt") as f:
            format_type = f.read().strip()
    print(f"📐 Video Format: {format_type}")

    video_files = sorted(
        [f for f in os.listdir(INPUT_DIR) if f.endswith(".mp4")],
        key=lambda x: int(re.search(r'\d+', x).group())
    )

    if not video_files:
        print("❌ No videos found!")
        return

    processed_clips = []
    for v_name in video_files:
        idx = int(re.search(r'\d+', v_name).group())
        clip = process_clip(os.path.join(INPUT_DIR, v_name), idx, format_type)
        if clip:
            processed_clips.append(clip)

    if not processed_clips:
        print("❌ No clips processed!")
        return

    # सारी क्लिप्स को Hard Cut से जोड़ना (No Fade)
    list_path = "list.txt"
    with open(list_path, "w") as f:
        for clip in processed_clips:
            f.write(f"file '{clip}'\n")

    temp_output = os.path.join(OUTPUT_DIR, "temp_master.mp4")
    print("🔗 Merging all clips with Hard Cuts...")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", temp_output],
        check=True
    )

    final_output = os.path.join(OUTPUT_DIR, "Final_4K_Monetizable.mp4")

    # BGM Mixing (Narrator 100%, Music 15%)
    if os.path.exists("bgm.wav"):
        print("🎵 Mixing BGM at 15% volume...")
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_output,
            "-stream_loop", "-1", "-i", "bgm.wav",
            "-filter_complex",
            "[0:a]volume=1.0[a1];[1:a]volume=0.15[a2];[a1][a2]amix=inputs=2:duration=first[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            final_output
        ]
        subprocess.run(cmd, check=True)
        print("🎉 Final video with BGM ready!")
    else:
        os.rename(temp_output, final_output)
        print("🎉 Final video (no BGM) ready!")

    size = os.path.getsize(final_output) / (1024 * 1024)
    print(f"📁 Final File: {final_output} ({size:.1f} MB)")

if __name__ == "__main__":
    main()
