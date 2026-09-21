import sys
import os
import asyncio
import json
import re
from playwright.async_api import async_playwright

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
SAVE_FOLDER = "scene_images"
os.makedirs(SAVE_FOLDER, exist_ok=True)

async def generate_single_image(scene_id, prompt_text):
    out_img_path = os.path.join(SAVE_FOLDER, f"scene_{scene_id}.jpg")
    
    if os.path.exists(out_img_path):
        print(f"⏭️ Scene {scene_id} image already exists. Skipping.")
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
                
                print("✅ Render complete! Waiting 5s for FULL HD load...")
                await asyncio.sleep(5) 
                
                async with page.expect_download() as download_info:
                    await download_btn.click()
                
                download = await download_info.value
                await download.save_as(out_img_path)
                
                await browser.close()
                print(f"✅ [Scene {scene_id}] RAW HD Image Saved Perfectly!")
                return True 
                
            except Exception as e:
                print(f"⚠️ Error on Attempt {attempt}: {str(e)[:50]}... Retrying!")
                await browser.close()
                await asyncio.sleep(4) 
                
        print(f"❌ All {max_retries} attempts FAILED for Scene {scene_id}.")
        return False

async def main():
    with open("script_data.json", "r", encoding="utf-8") as f:
        scenes = json.load(f)

    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else None

    if machine_id:
        scene = next((s for s in scenes if s["scene"] == machine_id), None)
        if scene:
            await generate_single_image(machine_id, scene["image_prompt"])

if __name__ == "__main__":
    asyncio.run(main())
