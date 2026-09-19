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
        urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf", FONT_FILE)

def process_smooth_fade(v_path, index):
    out_path = os.path.join(OUTPUT_DIR, f"clip_{index}.mp4")
    fade_dur = 0.5
    drawtext = f",drawtext=fontfile={FONT_FILE}:text='{CHANNEL_NAME}':fontcolor=white@0.5:fontsize=50:x=(w-text_w)/2:y=100" if os.path.exists(FONT_FILE) else ""
    
    vf = f"scale=1080:1920:flags=lanczos:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,format=yuv420p,fade=t=in:st=0:d={fade_dur},fade=t=out:st=4.5:d={fade_dur}{drawtext}"
    af = f"volume=2.0,afade=t=in:st=0:d={fade_dur},afade=t=out:st=4.5:d={fade_dur}"
    
    subprocess.run(["ffmpeg", "-y", "-i", v_path, "-vf", vf, "-af", af, "-c:v", "libx264", "-crf", "23", "-preset", "veryfast", "-c:a", "aac", "-b:a", "320k", out_path], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return out_path

def generate_voiceover():
    # 🔴 AI Dialogue ko Audio me convert karta hai (Edge TTS)
    if os.path.exists("dialogue.txt"):
        with open("dialogue.txt", "r", encoding="utf-8") as f:
            text = f.read().strip()
        if text:
            print(f"🎙️ Generating Voiceover for Scene 1: {text}")
            subprocess.run(["edge-tts", "--text", text, "--voice", "hi-IN-MadhurNeural", "--write-media", "voice.mp3"], check=True)
            return True
    return False

def main():
    video_files = [f for f in os.listdir(INPUT_DIR) if f.startswith("video_") and f.endswith(".mp4")]
    if not video_files: return

    download_font()
    has_voice = generate_voiceover() # Voice check & generate
    
    video_files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
    list_path = "list.txt"
    with open(list_path, "w") as f:
        for v_name in video_files:
            idx = int(re.search(r'\d+', v_name).group())
            clip_path = process_smooth_fade(os.path.join(INPUT_DIR, v_name), idx)
            f.write(f"file '{clip_path}'\n")

    temp_output = os.path.join(OUTPUT_DIR, "temp_master.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", temp_output], check=True)

    final_output = os.path.join(OUTPUT_DIR, "Final_4K_Monetizable_Short.mp4")

    # 🔴 Yahan BGM aur Voiceover (agar hai) dono ko mix kiya ja raha hai
    if os.path.exists("bgm.wav") and has_voice:
        print("🎵 Mixing BGM + Scene 1 Voiceover...")
        cmd = [
            "ffmpeg", "-y", "-i", temp_output, "-stream_loop", "-1", "-i", "bgm.wav", "-i", "voice.mp3",
            "-filter_complex", "[0:a]volume=1.0[v_aud];[1:a]volume=0.6[bgm];[2:a]volume=3.0[voice];[v_aud][bgm][voice]amix=inputs=3:duration=first:dropout_transition=2[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", final_output
        ]
    elif os.path.exists("bgm.wav"):
        cmd = [
            "ffmpeg", "-y", "-i", temp_output, "-stream_loop", "-1", "-i", "bgm.wav",
            "-filter_complex", "[0:a]volume=1.0[a1];[1:a]volume=0.8[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[a]", 
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", final_output
        ]
    else:
        os.rename(temp_output, final_output)
        return

    subprocess.run(cmd, check=True)
    print("🎉 FINAL VIDEO RENDERED SUCCESSFULLY!")

if __name__ == "__main__": 
    main()
