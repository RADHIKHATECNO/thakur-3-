import os
import subprocess
import re

INPUT_DIR = "generated_videos"
AUDIO_DIR = "scene_audio"
OUTPUT_DIR = "final_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def main():
    video_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".mp4")]
    if not video_files:
        return

    # Check Format (SHORT = 9:16, LONG = 16:9)
    format_type = "SHORT"
    if os.path.exists("video_format.txt"):
        with open("video_format.txt", "r") as f:
            format_type = f.read().strip()

    if format_type == "SHORT":
        scale_crop = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    else:
        scale_crop = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"

    video_files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
    processed_clips = []
    
    print(f"✂️ Processing clips as {format_type} with HARD CUTS & Voice Sync...")
    
    for v_name in video_files:
        idx = int(re.search(r'\d+', v_name).group())
        v_path = os.path.join(INPUT_DIR, v_name)
        voice_path = os.path.join(AUDIO_DIR, f"voice_{idx}.mp3")
        out_path = os.path.join(OUTPUT_DIR, f"clip_{idx}.mp4")
        
        # अगर उस सीन की आवाज़ है, तो वीडियो और आवाज़ को सिंक करो (-shortest कमांड से)
        if os.path.exists(voice_path):
            vf = f"{scale_crop},setsar=1,fps=30,format=yuv420p"
            cmd = [
                "ffmpeg", "-y", 
                "-stream_loop", "-1", "-i", v_path, # वीडियो छोटी हो तो लूप करो
                "-i", voice_path,                   # आवाज़ जोड़ो
                "-vf", vf, 
                "-c:v", "libx264", "-crf", "23", "-preset", "fast", 
                "-c:a", "aac", "-b:a", "192k", 
                "-shortest", # आवाज़ खत्म होते ही वीडियो कट (Hard Cut)
                out_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            processed_clips.append(out_path)

    # क्लिप्स को जोड़ना (Hard Cuts - No fade)
    list_path = "list.txt"
    with open(list_path, "w") as f:
        for clip in processed_clips: 
            f.write(f"file '{clip}'\n")

    temp_output = os.path.join(OUTPUT_DIR, "temp_master.mp4")
    print("🎬 Merging all synced clips...")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", temp_output], check=True)

    final_output = os.path.join(OUTPUT_DIR, "Final_4K_Monetizable.mp4")

    # BGM मिक्स करना (आवाज़ 100%, म्यूजिक सिर्फ़ 15% ताकि नैरेटर साफ़ सुनाई दे)
    if os.path.exists("bgm.wav"):
        print("🎵 Mixing BGM at 15% volume...")
        cmd = [
            "ffmpeg", "-y", 
            "-i", temp_output, 
            "-stream_loop", "-1", "-i", "bgm.wav", 
            "-filter_complex", "[0:a]volume=1.0[a1];[1:a]volume=0.15[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[a]", 
            "-map", "0:v", "-map", "[a]", 
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", final_output
        ]
        subprocess.run(cmd, check=True)
    else:
        os.rename(temp_output, final_output)
        
    print("🎉 MASTERPIECE GENERATED SUCCESSFULLY!")

if __name__ == "__main__": 
    main()
