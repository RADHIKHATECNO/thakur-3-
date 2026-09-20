import os
import subprocess
import sys

MUSIC_FILE  = "music_prompt.txt"
OUTPUT_FILE = "bgm.wav"

# ============================================================
# CARTOON SFX DOWNLOADER
# ============================================================
def download_cartoon_sfx():
    """
    Free cartoon SFX download karo
    Freesound API se
    """
    sfx_list = {
        "boing.wav"  : "https://www.soundjay.com/misc/sounds/boing-1.wav",
        "crash.wav"  : "https://www.soundjay.com/misc/sounds/fail-buzzer-01.wav",
        "whoosh.wav" : "https://www.soundjay.com/misc/sounds/swoosh-1.wav",
    }

    os.makedirs("sfx", exist_ok=True)

    import requests
    for name, url in sfx_list.items():
        path = os.path.join("sfx", name)
        if not os.path.exists(path):
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    with open(path, "wb") as f:
                        f.write(r.content)
                    print(f"✅ {name} downloaded!")
            except:
                print(f"⚠️ {name} download failed!")

# ============================================================
# CARTOON BGM GENERATOR
# ============================================================
def generate_cartoon_bgm():
    """
    Cartoon style BGM generate karo
    FFmpeg se sine wave + filters use karke
    Bilkul free!
    """
    print("🎵 Generating Cartoon BGM...")

    try:
        # Tom & Jerry style upbeat cartoon music
        # FFmpeg sine waves combine karke banao
        cmd = [
            "ffmpeg", "-y",

            # Base melody - C major scale
            "-f", "lavfi",
            "-i", (
                "aevalsrc="
                "0.3*sin(523*2*PI*t)+"    # C5
                "0.2*sin(659*2*PI*t)+"    # E5
                "0.15*sin(784*2*PI*t)+"   # G5
                "0.1*sin(1047*2*PI*t)+"   # C6
                "0.3*sin(261*2*PI*t)*"    # C4 bass
                "sin(4*2*PI*t):"          # 4Hz tremolo
                "s=44100:c=stereo"
            ),

            # Percussion layer
            "-f", "lavfi",
            "-i", (
                "aevalsrc="
                "0.4*sin(200*2*PI*t)*"
                "exp(-10*mod(t,0.5))+"    # Bass drum every 0.5s
                "0.2*sin(800*2*PI*t)*"
                "exp(-20*mod(t,0.25)):"   # Snare every 0.25s
                "s=44100:c=stereo"
            ),

            # Mix + Effects
            "-filter_complex",
            (
                "[0:a]volume=0.7[melody];"
                "[1:a]volume=0.3[perc];"
                "[melody][perc]amix=inputs=2:duration=longest[mix];"
                "[mix]"
                "aecho=0.8:0.9:40:0.4,"   # Echo for cartoon feel
                "equalizer=f=200:t=o:w=100:g=3,"  # Bass boost
                "equalizer=f=3000:t=o:w=500:g=2," # Treble boost
                "volume=2.0"
                "[out]"
            ),
            "-map", "[out]",
            "-t", "30",           # 30 seconds
            "-ar", "44100",
            "-ac", "2",
            OUTPUT_FILE
        ]

        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if os.path.exists(OUTPUT_FILE):
            size = os.path.getsize(OUTPUT_FILE)
            print(f"✅ Cartoon BGM ready! ({size} bytes)")
            return True

    except Exception as e:
        print(f"⚠️ Complex BGM failed: {e}")
        print("🔄 Trying simple BGM...")

        # Simple fallback BGM
        try:
            simple_cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", (
                    "aevalsrc="
                    "0.5*sin(440*2*PI*t)+"
                    "0.3*sin(554*2*PI*t)+"
                    "0.2*sin(659*2*PI*t):"
                    "s=44100:c=stereo"
                ),
                "-t", "30",
                "-ar", "44100",
                OUTPUT_FILE
            ]
            subprocess.run(
                simple_cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print("✅ Simple BGM ready!")
            return True

        except Exception as e2:
            print(f"❌ BGM generation failed: {e2}")
            return False

# ============================================================
# SFX EXTRACTOR FROM PROMPTS
# ============================================================
def extract_sfx_list():
    """
    prompts.txt se SFX list nikalo
    Har scene ke liye
    """
    if not os.path.exists("prompts.txt"):
        return {}

    sfx_map = {}
    with open("prompts.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if ">>" in line:
            parts = line.split(">>")
            if len(parts) >= 3:
                sfx_text = parts[2].strip()
                sfx_map[idx] = sfx_text
                print(f"   🔊 Scene {idx}: {sfx_text[:60]}...")

    print(f"✅ {len(sfx_map)} SFX descriptions extracted!")
    return sfx_map

# ============================================================
# MAIN
# ============================================================
def main():
    print("\n" + "="*50)
    print("🎵 CARTOON BGM + SFX GENERATOR")
    print("="*50 + "\n")

    # BGM generate
    print("🎬 Generating Tom & Jerry style BGM...")
    success = generate_cartoon_bgm()

    if success:
        print("✅ BGM ready!")
    else:
        print("⚠️ BGM failed - video will have no music")

    # SFX list extract
    print("\n🔊 Extracting SFX descriptions...")
    sfx_map = extract_sfx_list()

    # Save SFX map
    with open("sfx_map.json", "w", encoding="utf-8") as f:
        json.dump(sfx_map, f, indent=2, ensure_ascii=False)

    print("\n" + "="*50)
    print("🎉 Music Generation Complete!")
    print("="*50)

import json
if __name__ == "__main__":
    main()
