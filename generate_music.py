import os
import scipy.io.wavfile
import torch
from transformers import MusicgenForConditionalGeneration, AutoProcessor

def generate_local_ai_music():
    prompt = "epic emotional cinematic storytelling background score"
    if os.path.exists("music_prompt.txt"):
        with open("music_prompt.txt", "r", encoding="utf-8") as f:
            prompt = f.read().strip()

    print(f"🎵 LOCAL AI is Composing Music for: '{prompt}'")
    print("⏳ AI is generating a 15-second loopable masterpiece...")

    try:
        processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
        model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")

        inputs = processor(
            text=[prompt],
            padding=True,
            return_tensors="pt",
        )

        # max_new_tokens=768 generates approx 15-18 seconds of high-quality audio
        # We will loop this later in FFmpeg to match the 6-minute video length.
        audio_values = model.generate(**inputs, max_new_tokens=768)

        sampling_rate = model.config.audio_encoder.sampling_rate
        scipy.io.wavfile.write("bgm.wav", rate=sampling_rate, data=audio_values[0, 0].numpy())
        
        print("✅ 15-Sec AI BGM Loop Generated Successfully (bgm.wav)!")

    except Exception as e:
        print(f"❌ Local AI Generation Failed: {e}")
        print("⚠️ Video will be rendered without background music this time.")

if __name__ == "__main__":
    generate_local_ai_music()
