import sys
import os
import asyncio
import json
import re
import requests
from playwright.async_api import async_playwright

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
SAVE_FOLDER = "scene_images"
os.makedirs(SAVE_FOLDER, exist_ok=True)

def send_telegram_photo(photo_path, caption=""):
    if not BOT_TOKEN or not CHAT_ID: return
    try:
        with open(photo_path, "rb") as file:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": file}, timeout=15)
    except: pass

async def live_screenshot_tracker(page, scene_id, stop_event):
    sec = 10
    while not stop_event.is_set():
        await asyncio.sleep(10)
        if stop_event.is_set(): break
        try:
            shot_path = os.path.join(SAVE_FOLDER, f"live_img_s{scene_id}.png")
            await page.screenshot(path=shot_path)
            send_telegram_photo(shot_path, f"👀 [Scene {scene_id}] Live Status: {sec} sec...")
            sec += 10
        except: pass

async def generate_single_image(scene_id, prompt_text, video_format):
    out_img_path = os.path.join(SAVE_FOLDER, f"scene_{scene_id}.jpg")
    
    if os.path.exists(out_img_path): return True

    # Bing safety limit
    clean_prompt = re.sub(r'--ar\s+\d+:\d+', '', prompt_text).strip()[:450]
    
    async with async_playwright() as p:
        for attempt in range(1, 6):
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
                
                try: await page.locator("text='We are generating'").wait_for(state="detached", timeout=90000)
                except: pass 

                download_btn = page.locator("button[title='Download']:not([disabled]), a:has-text('Download')").first
                await download_btn.wait_for(state="visible", timeout=60000)
                await asyncio.sleep(5) 
                
                async with page.expect_download() as download_info:
                    await download_btn.click()
                
                download = await download_info.value
                # Direct save RAW for perfect FFmpeg crop
                await download.save_as(out_img_path)
                stop_tracker.set()
                await browser.close()
                
                send_telegram_photo(out_img_path, f"✅ [Scene {scene_id}] RAW HD Image Downloaded Perfectly!")
                return True 
            except Exception as e:
                stop_tracker.set()
                await browser.close()
                await asyncio.sleep(4) 
        return False

async def main():
    with open("client_setup.json", "r") as f: fmt = json.load(f).get("video_format", "long")
    with open("script_data.json", "r", encoding="utf-8") as f: scenes = json.load(f)
    
    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if machine_id:
        scene = next((s for s in scenes if s["scene"] == machine_id), None)
        if scene: await generate_single_image(machine_id, scene["image_prompt"], fmt)

if __name__ == "__main__":
    asyncio.run(main())
