import sys
import os
import asyncio
import json
import re
from playwright.async_api import async_playwright
from PIL import Image, ImageFilter

SAVE_FOLDER = "scene_images"
os.makedirs(SAVE_FOLDER, exist_ok=True)

# Smart Cropper: 1:1 Image ko 16:9 ya 9:16 mein badalna
def smart_crop_image(image_path, video_format):
    try:
        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size
        
        # Dimensions set karna client config ke hisaab se
        if video_format.lower() == "short":
            target_w, target_h = 1080, 1920 # 9:16 for Shorts/Reels
        else:
            target_w, target_h = 1920, 1080 # 16:9 for YouTube Long

        print(f"🎨 Formatting image to {target_w}x{target_h} ({video_format.upper()})...")

        # 1. Background Layer (Stretch & Blur)
        bg = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(50)) # Deep cinematic blur

        # 2. Foreground Layer (Fit main image cleanly)
        if video_format.lower() == "short":
            # Reel ke liye height fit karenge, width adjust hogi
            new_w = target_w
            new_h = int((new_w / orig_w) * orig_h)
            offset_x = 0
            offset_y = (target_h - new_h) // 2
        else:
            # YouTube ke liye height 1080 fix, width adjust hogi
            new_h = target_h
            new_w = int((new_h / orig_h) * orig_w)
            offset_x = (target_w - new_w) // 2
            offset_y = 0

        fg = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 3. Merge Background & Foreground
        bg.paste(fg, (offset_x, offset_y))
        bg.save(image_path, format="JPEG", quality=98)
        print(f"✅ {video_format.upper()} Format Ready for video!")
        
    except Exception as e:
        print(f"⚠️ Image crop failed: {e}")

async def generate_single_image(scene_id, prompt_text, video_format):
    out_img_path = os.path.join(SAVE_FOLDER, f"scene_{scene_id}.jpg")
    
    # Check if already exists (GitHub cache/resume support)
    if os.path.exists(out_img_path):
        print(f"⏭️ Image for Scene {scene_id} already exists. Skipping generation.")
        return True

    clean_prompt = re.sub(r'--ar\s+\d+:\d+', '', prompt_text).strip()
    max_retries = 5

    async with async_playwright() as p:
        for attempt in range(1, max_retries + 1):
            print(f"\n🔄 [Attempt {attempt}/{max_retries}] Scraping Bing for Scene {scene_id}...")
            
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width': 1280, 'height': 720})
            page = await context.new_page()

            try:
                await page.goto("https://www.bing.com/images/create", timeout=60000)
                await asyncio.sleep(2)
                
                await page.locator("textarea, input[placeholder*='Describe']").first.fill(clean_prompt)
                await page.locator("button:has-text('Generate'), button:has-text('Create')").first.click()
                
                print("⏳ Waiting for Bing to generate...")
                try:
                    await page.locator("text='We are generating'").wait_for(state="detached", timeout=90000)
                except:
                    pass 

                download_btn = page.locator("button[title='Download']:not([disabled]), a:has-text('Download')").first
                await download_btn.wait_for(state="visible", timeout=60000)
                
                print("✅ Render complete! Waiting 5 extra seconds for FULL HD load...")
                await asyncio.sleep(5) 
                
                async with page.expect_download() as download_info:
                    await download_btn.click()
                
                download = await download_info.value
                await download.save_as(out_img_path)
                
                await browser.close()
                
                # Download hote hi turant format theek karo!
                smart_crop_image(out_img_path, video_format)
                return True 
                
            except Exception as e:
                print(f"⚠️ Error on Attempt {attempt}: {str(e)[:50]}... Retrying!")
                await browser.close()
                await asyncio.sleep(4) 
                
        print(f"❌ All {max_retries} attempts FAILED for Scene {scene_id}.")
        return False

async def main():
    if not os.path.exists("script_data.json") or not os.path.exists("client_setup.json"):
        print("❌ ERROR: Required JSON files are missing!")
        return

    # Client config se video format pata karo (short or long)
    with open("client_setup.json", "r") as f:
        config = json.load(f)
        video_format = config.get("video_format", "long")

    # Script se scene details nikalo
    with open("script_data.json", "r", encoding="utf-8") as f:
        scenes = json.load(f)

    # Agar action mein matrix id pass hua hai, toh sirf ek image banayega. Warna saari banayega.
    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else None

    if machine_id:
        # Sirf specific scene (GitHub Matrix support)
        scene = next((s for s in scenes if s["scene"] == machine_id), None)
        if scene:
            await generate_single_image(machine_id, scene["image_prompt"], video_format)
    else:
        # Local run ke liye saari images ek sath banayega
        for scene in scenes:
            await generate_single_image(scene["scene"], scene["image_prompt"], video_format)

if __name__ == "__main__":
    asyncio.run(main())
