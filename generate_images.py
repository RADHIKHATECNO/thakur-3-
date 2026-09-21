import sys
import os
import asyncio
import json
import re
import requests
from playwright.async_api import async_playwright
from PIL import Image, ImageFilter

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
SAVE_FOLDER = "scene_images"
os.makedirs(SAVE_FOLDER, exist_ok=True)

def send_telegram_photo(photo_path, caption=""):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        with open(photo_path, "rb") as file:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", 
                data={"chat_id": CHAT_ID, "caption": caption}, 
                files={"photo": file}, 
                timeout=15
            )
    except:
        pass

async def live_screenshot_tracker(page, scene_id, stop_event):
    sec = 10
    while not stop_event.is_set():
        await asyncio.sleep(10)
        if stop_event.is_set():
            break
        try:
            shot_path = os.path.join(SAVE_FOLDER, f"live_img_s{scene_id}.png")
            await page.screenshot(path=shot_path)
            send_telegram_photo(shot_path, f"👀 [Scene {scene_id}] Live Status: {sec} sec...")
            sec += 10
        except:
            pass

# Smart Cropper: 1:1 Image ko 16:9 ya 9:16 mein badalna
def smart_crop_image(image_path, video_format, scene_id):
    try:
        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size
        
        if video_format.lower() == "short":
            target_w, target_h = 1080, 1920 # 9:16 for Shorts/Reels
        else:
            target_w, target_h = 1920, 1080 # 16:9 for YouTube Long

        # Background Layer (Stretch & Blur)
        bg = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(50))

        # Foreground Layer (Fit main image cleanly)
        if video_format.lower() == "short":
            new_w = target_w
            new_h = int((new_w / orig_w) * orig_h)
            offset_x = 0
            offset_y = (target_h - new_h) // 2
        else:
            new_h = target_h
            new_w = int((new_h / orig_h) * orig_w)
            offset_x = (target_w - new_w) // 2
            offset_y = 0

        fg = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Merge Background & Foreground
        bg.paste(fg, (offset_x, offset_y))
        bg.save(image_path, format="JPEG", quality=98)
        
        # Telegram pe Final HD image bhejna
        send_telegram_photo(image_path, f"✅ [Scene {scene_id}] Final {video_format.upper()} Image Ready & Cropped!")
        
    except Exception as e:
        print(f"⚠️ Image crop failed: {e}")

async def generate_single_image(scene_id, prompt_text, video_format):
    out_img_path = os.path.join(SAVE_FOLDER, f"scene_{scene_id}.jpg")
    clean_prompt = re.sub(r'--ar\s+\d+:\d+', '', prompt_text).strip()
    max_retries = 5

    async with async_playwright() as p:
        for attempt in range(1, max_retries + 1):
            print(f"\n🔄 [Attempt {attempt}/{max_retries}] Scraping Bing for Scene {scene_id}...")
            
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width': 1280, 'height': 720})
            page = await context.new_page()
            
            stop_tracker = asyncio.Event()
            asyncio.create_task(live_screenshot_tracker(page, scene_id, stop_tracker))

            try:
                await page.goto("https://www.bing.com/images/create", timeout=60000)
                await asyncio.sleep(3)
                
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
                
                stop_tracker.set()
                await browser.close()
                
                # Auto-crop aur Telegram pe final bhejna
                smart_crop_image(out_img_path, video_format, scene_id)
                return True 
                
            except Exception as e:
                print(f"⚠️ Error on Attempt {attempt}: {str(e)[:50]}... Retrying!")
                stop_tracker.set()
                await browser.close()
                await asyncio.sleep(4) 
                
        print(f"❌ All {max_retries} attempts FAILED for Scene {scene_id}.")
        return False

async def main():
    with open("client_setup.json", "r") as f:
        video_format = json.load(f).get("video_format", "long")

    with open("script_data.json", "r", encoding="utf-8") as f:
        scenes = json.load(f)

    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else None

    if machine_id:
        scene = next((s for s in scenes if s["scene"] == machine_id), None)
        if scene:
            await generate_single_image(machine_id, scene["image_prompt"], video_format)

if __name__ == "__main__":
    asyncio.run(main())
