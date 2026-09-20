import os
import subprocess
import shutil

def process():
    os.makedirs("final_output", exist_ok=True)
    
    videos = [f for f in os.listdir("generated_videos") if f.endswith(".mp4")]
    if not videos:
        print("❌ Error: No videos found to merge!")
        return

    print("🎬 Merging Videos...")
    # Merge list file
    with open("list.txt", "w") as f:
        for v in videos:
            f.write(f"file 'generated_videos/{v}'\n")
            # Add voiceover if exists
    voice = "voiceover.wav"
    if os.path.exists(voice):
        subprocess.run(["ffmpeg", "-y", "-i", "list.txt", "-i", voice, "-filter_complex", "[1:a]volume=0.5[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-ar", "44100", "final_output/merged.mp4"])
        print("✅ Merged with Voiceover")
    else:
        subprocess.run(["ffmpeg", "-y", "-i", "list.txt", "-c", "copy", "final_output/merged.mp4"])
        print("✅ Merged (No Voice)")

    print("🎬 Ready for Upload")

if __name__ == "__main__":
    process()
