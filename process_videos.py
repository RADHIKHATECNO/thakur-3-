import os
import json
import subprocess
import re
import urllib.request

# ============================================================
# CONFIG
# ============================================================
INPUT_DIR   = "generated_videos"
VOICE_DIR   = "scene_voices"
OUTPUT_DIR  = "final_output"
CONFIG_FILE = "video_config.json"
SFX_FILE    = "sfx_map.json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

CHANNEL_NAME = "@THAKURSAHAB"
FONT_FILE    = "Roboto-Bold.ttf"

# ============================================================
# FONT
# ============================================================
def download_font():
    if not os.path.exists(FONT_FILE):
        print("📥 Downloading font...")
        try:
            urllib.request.urlretrieve(
                "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
                FONT_FILE
            )
            print("✅ Font ready!")
        except:
            print("⚠️ Font download failed!")

# ============================================================
# CONFIG LOADER
# ============================================================
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "video_type"  : "short",
        "aspect_ratio": "9:16"
    }

def load_sfx_map():
    if os.path.exists(SFX_FILE):
        with open(SFX_FILE, "r") as f:
            return json.load(f)
    return {}

# ============================================================
# RESOLUTION
# ============================================================
def get_resolution(aspect_ratio):
    if aspect_ratio == "9:16":
        return "1080:1920"
    else:
        return "1920:1080"

# ============================================================
# CARTOON SPEED EFFECT
# ============================================================
def add_cartoon_effects(
    video_path, scene_id,
    aspect_ratio, output_path
):
    """
    Tom & Jerry style effects:
    - Speed up funny parts
    - Zoom effects
    - Bright colors
    - No fade transitions
    - Watermark
    """
    resolution = get_resolution(aspect_ratio)

    # Watermark
    if os.path.exists(FONT_FILE):
        watermark = (
            f",drawtext="
            f"fontfile={FONT_FILE}:"
            f"text='{CHANNEL_NAME}':"
            f"fontcolor=white@0.5:"
            f"fontsize=45:"
            f"x=(w-text_w)/2:"
            f"y=80"
        )
    else:
        watermark = ""

    # Tom & Jerry style filter
    vf = (
        f"scale={resolution}:"
        f"flags=lanczos:"
        f"force_original_aspect_ratio=increase,"
        f"crop={resolution},"
        f"setsar=1,"
        f"fps=30,"
        # Bright vivid colors like cartoon
        f"eq=saturation=1.4:brightness=0.05:contrast=1.1,"
        f"format=yuv420p"
        f"{watermark}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",   # Loop video
        "-i", video_path,
        "-vf", vf,
        "-t", "5",              # 5 seconds per clip
        "-c:v", "libx264",
        "-crf", "20",
        "-preset", "veryfast",
        "-an",                  # No audio (BGM baad mein add)
        output_path
    ]

    print(f"⚙️  Processing Scene {scene_id}...")
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(f"✅ Scene {scene_id} processed!")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"❌ Scene {scene_id} failed!")
        print(f"   {e.stderr.decode()[-200:]}")
        return None

# ============================================================
# SEAMLESS MERGE
# ============================================================
def seamless_merge(clip_paths, output_path):
    """
    Clips ko seamlessly merge karo
    Tom & Jerry style - abrupt cuts (no fade)
    """
    if not clip_paths:
        print("❌ No clips!")
        return False

    if len(clip_paths) == 1:
        subprocess.run(
            ["cp", clip_paths[0], output_path],
            check=True
        )
        return True

    print(f"\n🎬 Merging {len(clip_paths)} clips...")

    # List file
    list_path = os.path.join(OUTPUT_DIR, "list.txt")
    with open(list_path, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    # Simple concat - Tom & Jerry style hard cuts
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_path,
        "-c:v", "libx264",
        "-crf", "20",
        "-preset", "veryfast",
        "-an",
        output_path
    ]

    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ Merge complete!")
        return True
    except Exception as e:
        print(f"❌ Merge failed: {e}")
        return False

# ============================================================
# OUTRO PROCESSOR
# ============================================================
def process_outro(aspect_ratio):
    if not os.path.exists("outro.mp4"):
        return None

    outro_out  = os.path.join(OUTPUT_DIR, "outro_processed.mp4")
    resolution = get_resolution(aspect_ratio)

    vf = (
        f"scale={resolution}:"
        f"flags=lanczos:"
        f"force_original_aspect_ratio=increase,"
        f"crop={resolution},"
        f"setsar=1,fps=30,"
        f"eq=saturation=1.4:brightness=0.05,"
        f"format=yuv420p"
    )

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", "outro.mp4",
                "-vf", vf,
                "-c:v", "libx264",
                "-crf", "20",
                "-preset", "veryfast",
                "-an",
                outro_out
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ Outro processed!")
        return outro_out
    except Exception as e:
        print(f"⚠️ Outro failed: {e}")
        return None

# ============================================================
# BGM MIXER - TOM & JERRY STYLE
# ============================================================
def mix_cartoon_bgm(video_path, output_path):
    """
    Cartoon BGM mix karo
    Upbeat funny music
    """
    if not os.path.exists("bgm.wav"):
        print("⚠️ No BGM! Copying without music...")
        subprocess.run(["cp", video_path, output_path])
        return

    print("🎵 Mixing cartoon BGM...")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-stream_loop", "-1",
        "-i", "bgm.wav",
        "-filter_complex",
        (
            # BGM volume - cartoon style loud and fun
            "[1:a]volume=0.8[bgm];"
            "[bgm]"
            # Slight EQ for cartoon feel
            "equalizer=f=300:t=o:w=200:g=2,"
            "equalizer=f=5000:t=o:w=1000:g=1"
            "[audio]"
        ),
        "-map", "0:v",
        "-map", "[audio]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_path
    ]

    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ BGM mixed!")
    except Exception as e:
        print(f"⚠️ BGM mix failed: {e}")
        subprocess.run(["cp", video_path, output_path])

# ============================================================
# MAIN
# ============================================================
def main():
    print("\n" + "="*50)
    print("🎬 TOM & JERRY STYLE PROCESSOR")
    print("="*50 + "\n")

    config       = load_config()
    sfx_map      = load_sfx_map()
    aspect_ratio = config.get("aspect_ratio", "9:16")
    video_type   = config.get("video_type", "short")

    print(f"📺 Type  : {video_type.upper()}")
    print(f"📐 Ratio : {aspect_ratio}")

    download_font()

    # Videos sort
    video_files = sorted(
        [
            f for f in os.listdir(INPUT_DIR)
            if f.startswith("video_") and f.endswith(".mp4")
        ],
        key=lambda x: int(re.search(r'\d+', x).group())
    )

    if not video_files:
        print("❌ No videos found!")
        return

    print(f"\n📁 Found {len(video_files)} clips\n")

    # Process clips
    processed = []
    for v_name in video_files:
        scene_id = int(re.search(r'\d+', v_name).group())
        v_path   = os.path.join(INPUT_DIR, v_name)
        out_path = os.path.join(OUTPUT_DIR, f"clip_{scene_id}.mp4")

        result = add_cartoon_effects(
            v_path, scene_id,
            aspect_ratio, out_path
        )
        if result:
            processed.append(result)

    if not processed:
        print("❌ No clips processed!")
        return

    # Outro
    outro = process_outro(aspect_ratio)
    if outro:
        processed.append(outro)
        print("✅ Outro added!")

    # Merge
    merged = os.path.join(OUTPUT_DIR, "merged.mp4")
    if not seamless_merge(processed, merged):
        print("❌ Merge failed!")
        return

    # BGM mix
    final = os.path.join(
        OUTPUT_DIR,
        "Final_4K_Monetizable_Short.mp4"
    )
    mix_cartoon_bgm(merged, final)

    # Done!
    if os.path.exists(final):
        size = os.path.getsize(final) / (1024*1024)
        print(f"\n{'='*50}")
        print(f"🎉 TOM & JERRY VIDEO READY!")
        print(f"   📁 File  : {final}")
        print(f"   📦 Size  : {size:.1f} MB")
        print(f"   📐 Ratio : {aspect_ratio}")
        print(f"   🎬 Clips : {len(processed)}")
        print(f"{'='*50}\n")
    else:
        print("❌ Final video failed!")

if __name__ == "__main__":
    main()
