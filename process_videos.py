import os
import json
import subprocess
import re
import urllib.request

# ============================================================
# CONFIG
# ============================================================
INPUT_DIR  = "generated_videos"
VOICE_DIR  = "scene_voices"
OUTPUT_DIR = "final_output"
CONFIG_FILE = "video_config.json"
TIMING_FILE = "timing_map.json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

CHANNEL_NAME = "@THAKURSAHAB"
FONT_FILE    = "Roboto-Bold.ttf"

# ============================================================
# FONT DOWNLOAD
# ============================================================
def download_font():
    if not os.path.exists(FONT_FILE):
        print("📥 Downloading font...")
        try:
            urllib.request.urlretrieve(
                "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
                FONT_FILE
            )
            print("✅ Font downloaded!")
        except Exception as e:
            print(f"⚠️ Font download failed: {e}")

# ============================================================
# CONFIG LOADER
# ============================================================
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "video_type": "short",
        "aspect_ratio": "9:16",
        "duration_sec": 30
    }

def load_timing_map():
    if os.path.exists(TIMING_FILE):
        with open(TIMING_FILE, "r") as f:
            return json.load(f)
    return {}

# ============================================================
# VIDEO RESOLUTION
# ============================================================
def get_resolution(aspect_ratio):
    if aspect_ratio == "9:16":
        return "1080:1920"  # Shorts - Vertical
    else:
        return "1920:1080"  # Long - Horizontal

# ============================================================
# SEAMLESS TRANSITION PROCESSOR
# ============================================================
def process_clip_with_voice(
    video_path,
    voice_path,
    scene_id,
    aspect_ratio,
    voice_duration
):
    """
    Video + Voice ko seamlessly merge karo
    - Seamless transition (fade nahi)
    - Voice ke saath video sync karo
    - Watermark add karo
    """
    out_path = os.path.join(OUTPUT_DIR, f"clip_{scene_id}.mp4")
    resolution = get_resolution(aspect_ratio)

    # Watermark filter
    if os.path.exists(FONT_FILE):
        watermark = (
            f",drawtext=fontfile={FONT_FILE}:"
            f"text='{CHANNEL_NAME}':"
            f"fontcolor=white@0.6:"
            f"fontsize=45:"
            f"x=(w-text_w)/2:"
            f"y=80"
        )
    else:
        watermark = ""

    # Video filter - NO FADE, seamless
    # xfade use karenge clips join karne ke liye (main loop mein)
    vf = (
        f"scale={resolution}:"
        f"flags=lanczos:"
        f"force_original_aspect_ratio=increase,"
        f"crop={resolution},"
        f"setsar=1,"
        f"fps=30,"
        f"format=yuv420p"
        f"{watermark}"
    )

    if voice_path and os.path.exists(voice_path):
        # Voice ke saath merge karo
        # Video ko voice ki length tak trim/loop karo
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",  # Video loop karo agar voice zyada lambi ho
            "-i", video_path,
            "-i", voice_path,
            "-vf", vf,
            "-af", "volume=1.0",
            "-map", "0:v",
            "-map", "1:a",
            "-t", str(voice_duration),  # Voice duration tak hi rakho
            "-c:v", "libx264",
            "-crf", "20",
            "-preset", "veryfast",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            out_path
        ]
    else:
        # Sirf video (no voice)
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", vf,
            "-t", str(voice_duration),
            "-c:v", "libx264",
            "-crf", "20",
            "-preset", "veryfast",
            "-an",
            out_path
        ]

    print(f"⚙️  Processing Scene {scene_id} ({voice_duration:.1f}s)...")
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(f"✅ Scene {scene_id} processed!")
        return out_path
    except subprocess.CalledProcessError as e:
        print(f"❌ Scene {scene_id} processing failed!")
        print(f"   Error: {e.stderr.decode()[-200:]}")
        return None

# ============================================================
# SEAMLESS MERGE WITH XFADE
# ============================================================
def merge_with_xfade(clip_paths, output_path):
    """
    Clips ko seamlessly join karo XFADE transition se
    Viewer ko pata nahi chalega ki cut hua
    """
    if len(clip_paths) == 1:
        subprocess.run(
            ["cp", clip_paths[0], output_path],
            check=True
        )
        return

    print(f"\n🎬 Merging {len(clip_paths)} clips with SEAMLESS transitions...")

    # Pehle har clip ki duration nikalo
    durations = []
    for clip in clip_paths:
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-show_entries", "format=duration",
                    "-of", "csv=p=0", clip
                ],
                capture_output=True, text=True
            )
            dur = float(result.stdout.strip())
            durations.append(dur)
        except:
            durations.append(5.0)

    # Simple concat method (xfade complex filter)
    # Transition: 0.3 second smooth blend
    transition_dur = 0.3

    if len(clip_paths) == 2:
        # 2 clips ke liye simple xfade
        offset = max(0.1, durations[0] - transition_dur)
        cmd = [
            "ffmpeg", "-y",
            "-i", clip_paths[0],
            "-i", clip_paths[1],
            "-filter_complex",
            f"[0:v][1:v]xfade=transition=smoothleft:duration={transition_dur}:offset={offset}[v];"
            f"[0:a][1:a]acrossfade=d={transition_dur}[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-crf", "20",
            "-preset", "veryfast",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    else:
        # Multiple clips ke liye concat demuxer use karo
        # Phir xfade apply karo
        list_path = os.path.join(OUTPUT_DIR, "merge_list.txt")
        with open(list_path, "w") as f:
            for clip in clip_paths:
                f.write(f"file '{os.path.abspath(clip)}'\n")

        # Pehle simple concat
        temp_concat = os.path.join(OUTPUT_DIR, "temp_concat.mp4")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_path,
                "-c", "copy",
                temp_concat
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Phir smooth filter apply karo
        # unsharp + slight blur transition ke beech
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_concat,
            "-vf",
            "minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
            "-c:v", "libx264",
            "-crf", "20",
            "-preset", "veryfast",
            "-c:a", "copy",
            output_path
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except:
            # Fallback: simple copy
            subprocess.run(
                ["cp", temp_concat, output_path],
                check=True
            )

    print(f"✅ Seamless merge complete!")

# ============================================================
# OUTRO PROCESSOR
# ============================================================
def process_outro(aspect_ratio):
    if not os.path.exists("outro.mp4"):
        return None

    outro_out = os.path.join(OUTPUT_DIR, "processed_outro.mp4")
    resolution = get_resolution(aspect_ratio)

    vf = (
        f"scale={resolution}:"
        f"flags=lanczos:"
        f"force_original_aspect_ratio=increase,"
        f"crop={resolution},"
        f"setsar=1,fps=30,format=yuv420p"
    )

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", "outro.mp4",
                "-vf", vf,
                "-c:v", "libx264",
                "-crf", "23",
                "-preset", "veryfast",
                "-c:a", "aac",
                "-b:a", "192k",
                outro_out
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ Outro processed!")
        return outro_out
    except Exception as e:
        print(f"⚠️ Outro processing failed: {e}")
        return None

# ============================================================
# BGM MIXER
# ============================================================
def mix_bgm(input_video, output_video, video_type):
    """
    Background music mix karo
    Voice se zyada loud nahi hogi BGM
    """
    if not os.path.exists("bgm.wav"):
        print("⚠️ No BGM found. Skipping music mix.")
        subprocess.run(["cp", input_video, output_video])
        return

    # Short ke liye soft BGM, Long ke liye medium
    bgm_volume = "0.15" if video_type == "short" else "0.20"

    print(f"🎵 Mixing BGM (volume: {bgm_volume})...")

    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-stream_loop", "-1",
        "-i", "bgm.wav",
        "-filter_complex",
        (
            f"[0:a]volume=1.0[voice];"
            f"[1:a]volume={bgm_volume}[bgm];"
            f"[voice][bgm]amix=inputs=2:"
            f"duration=first:"
            f"dropout_transition=2[audio]"
        ),
        "-map", "0:v",
        "-map", "[audio]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        output_video
    ]

    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ BGM mixed successfully!")
    except Exception as e:
        print(f"⚠️ BGM mix failed: {e}. Using without BGM.")
        subprocess.run(["cp", input_video, output_video])

# ============================================================
# MAIN
# ============================================================
def main():
    print("\n" + "="*50)
    print("🎬 VIDEO PROCESSOR - SEAMLESS EDITION")
    print("="*50 + "\n")

    config      = load_config()
    timing_map  = load_timing_map()
    aspect_ratio = config.get("aspect_ratio", "9:16")
    video_type  = config.get("video_type", "short")

    print(f"📺 Type         : {video_type.upper()}")
    print(f"📐 Aspect Ratio : {aspect_ratio}")

    download_font()

    # Video files sort karo
    video_files = sorted(
        [f for f in os.listdir(INPUT_DIR)
         if f.startswith("video_") and f.endswith(".mp4")],
        key=lambda x: int(re.search(r'\d+', x).group())
    )

    if not video_files:
        print("❌ No videos found!")
        return

    print(f"\n📁 Found {len(video_files)} video clips\n")

    # Har clip ko process karo
    processed_clips = []

    for v_name in video_files:
        scene_id   = int(re.search(r'\d+', v_name).group())
        v_path     = os.path.join(INPUT_DIR, v_name)

        # Voice path
        voice_path = os.path.join(VOICE_DIR, f"voice_{scene_id}.mp3")
        if not os.path.exists(voice_path):
            voice_path = None

        # Duration from timing map
        scene_key = str(scene_id)
        if scene_key in timing_map:
            voice_dur = timing_map[scene_key].get("duration_sec", 5.0)
        else:
            voice_dur = 5.0

        # Process clip
        processed = process_clip_with_voice(
            v_path,
            voice_path,
            scene_id,
            aspect_ratio,
            voice_dur
        )

        if processed:
            processed_clips.append(processed)

    if not processed_clips:
        print("❌ No clips processed successfully!")
        return

    # Outro add karo
    outro_path = process_outro(aspect_ratio)
    if outro_path:
        processed_clips.append(outro_path)
        print("✅ Outro added!")

    # Seamless merge
    merged_path = os.path.join(OUTPUT_DIR, "merged_master.mp4")
    merge_with_xfade(processed_clips, merged_path)

    # BGM mix
    final_path = os.path.join(
        OUTPUT_DIR,
        "Final_4K_Monetizable_Short.mp4"
    )
    mix_bgm(merged_path, final_path, video_type)

    # Final stats
    if os.path.exists(final_path):
        size_mb = os.path.getsize(final_path) / (1024 * 1024)
        print(f"\n{'='*50}")
        print(f"🎉 FINAL VIDEO READY!")
        print(f"   📁 File   : {final_path}")
        print(f"   📦 Size   : {size_mb:.1f} MB")
        print(f"   📐 Ratio  : {aspect_ratio}")
        print(f"   🎬 Clips  : {len(processed_clips)}")
        print(f"{'='*50}\n")
    else:
        print("❌ Final video creation failed!")

if __name__ == "__main__":
    main()
