import os
import scipy.io.wavfile
import torch
from transformers import MusicgenForConditionalGeneration, AutoProcessor

def generate_local_ai_music():
    # 1. Prompt read karna (Jo AI ne story ke hisaab se banaya tha)
    prompt = "sad cinematic emotional piano"
    if os.path.exists("music_prompt.txt"):
        with open("music_prompt.txt", "r", encoding="utf-8") as f:
            prompt = f.read().strip()

    print(f"🎵 LOCAL AI is Composing Music for: '{prompt}'")
    print("⏳ Please wait 3 to 5 minutes. The AI is creating the track inside GitHub's CPU...")

    try:
        # 2. AI Model ko local memory me load karna (Sirf pehli baar download hoga, CPU par chalega)
        processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
        model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")

        # 3. Prompt ko AI ke samajhne layak format me convert karna
        inputs = processor(
            text=[prompt],
            padding=True,
            return_tensors="pt",
        )

        # 4. Generate audio (max_new_tokens=512 matlab lagbhag 10-12 second ka music)
        # Is gaane ko humara FFmpeg editor automatic loop kar dega poori video me.
        audio_values = model.generate(**inputs, max_new_tokens=512)

        # 5. Audio file ko wav format me save karna
        sampling_rate = model.config.audio_encoder.sampling_rate
        scipy.io.wavfile.write("bgm.wav", rate=sampling_rate, data=audio_values[0, 0].numpy())
        
        print("✅ 100% ORIGINAL LOCAL AI MUSIC GENERATED SUCCESSFULLY (bgm.wav)!")

    except Exception as e:
        print(f"❌ Local AI Generation Failed: {e}")
        print("⚠️ Video will be rendered without background music this time.")

if __name__ == "__main__":
    generate_local_ai_music()
