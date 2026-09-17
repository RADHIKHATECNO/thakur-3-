import sys
import os
import asyncio
import requests
import re
from playwright.async_api import async_playwright

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
SAVE_FOLDER = "scene_images"
PROMPT_FILE = "prompts.txt"
os.makedirs(SAVE_FOLDER, exist_ok=True)

def send_telegram_photo(photo_path, caption=""):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        with open(photo_path, "rb") as file:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": file}, timeout=15)
    except:
        pass

async def live_screenshot_tracker(page, machine_id, stop_event):
    sec = 10
    while not stop_event.is_set():
        await asyncio.sleep(10)
        if stop_event.is_set():
            break
        try:
            shot_path = os.path.join(SAVE_FOLDER, f"live_img_m{machine_id}.png")
            await page.screenshot(path=shot_path)
            send_telegram_photo(shot_path, f"👀 [Image M-{machine_id}] Live Status: {sec} sec...")
            sec += 10
        except:
            pass

async def generate_single_image(machine_id, prompt_text):
    out_img_path = os.path.join(SAVE_FOLDER, f"scene_{machine_id}.jpg")
    clean_prompt = re.sub(r'--ar\s+\d+:\d+', '', prompt_text).strip()
    
    # 🔴 YAHAN MAGIC HAI: 5 Baar try karne ka loop
    max_retries = 5

    async with async_playwright() as p:
        for attempt in range(1, max_retries + 1):
            print(f"\n🔄 [Attempt {attempt}/{max_retries}] Opening FRESH Browser for Scene {machine_id}...")
            
            # Har attempt mein naya browser khulega
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width': 1280, 'height': 720})
            page = await context.new_page()
            
            stop_tracker = asyncio.Event()
            asyncio.create_task(live_screenshot_tracker(page, machine_id, stop_tracker))
            
            try:
                await page.goto("https://www.bing.com/images/create", timeout=60000)
                await asyncio.sleep(3)
                
                await page.locator("textarea, input[placeholder*='Describe']").first.fill(clean_prompt)
                await asyncio.sleep(1)
                await page.locator("button:has-text('Generate'), button:has-text('Create')").first.click()
                
                print("⏳ Waiting for Bing to generate...")
                
                # Loading screen hatne ka wait karega
                try:
                    await page.locator("text='We are generating'").wait_for(state="detached", timeout=90000)
                except:
                    pass # Kabhi kabhi direct image aa jati hai bina loading text ke
                
                # Download button visible hone ka wait karega
                download_btn = page.locator("button[title='Download']:not([disabled]), a:has-text('Download')").first
                await download_btn.wait_for(state="visible", timeout=60000)
                
                # 🔴 CRITICAL FIX: Download button aane ke baad 5 second extra wait
                # Taaki image piche poori HD me load ho jaye, aadhi loading wali download na ho
                print("✅ Render complete! Waiting 5 extra seconds for FULL HD load...")
                await asyncio.sleep(5) 
                
                # Image save karna
                async with page.expect_download() as download_info:
                    await download_btn.click()
                
                download = await download_info.value
                await download.save_as(out_img_path)
                
                stop_tracker.set()
                send_telegram_photo(out_img_path, f"✅ [Scene {machine_id}] Image Created Successfully on Attempt {attempt}!")
                await browser.close()
                return True # Success milte hi loop se bahar aa jayega
                
            except Exception as e:
                # Agar fail hua, toh purana browser close aur loop me agla attempt shuru
                print(f"⚠️ Error on Attempt {attempt}: {str(e)[:50]}... Destroying browser and retrying!")
                stop_tracker.set()
                await browser.close()
                await asyncio.sleep(4) # Agla try karne se pehle thoda thanda hone do
                
        # Agar 5 ke 5 try fail ho gaye
        print(f"❌ All {max_retries} attempts FAILED for Scene {machine_id}. Skipping image.")
        return False

async def main():
    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    prompts = {}
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f.readlines(), 1):
                parts = line.strip().split("|")
                if len(parts) >= 1:
                    prompts[idx] = parts[0].strip() # 1st Part (Image)
                    
    await generate_single_image(machine_id, prompts.get(machine_id, "A cinematic shot of nature"))

if __name__ == "__main__":
    asyncio.run(main())
