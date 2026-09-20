import sys
import os
import asyncio
import requests
import re
from playwright.async_api import async_playwright

# Pillow library to convert Square images to 16:9 Landscape
try:
    from PIL import Image, ImageFilter
except ImportError:
    os.system("pip install pillow")
    from PIL import Image, ImageFilter

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
SAVE_FOLDER = "scene_images"
PROMPT_FILE = "prompts.txt"
os.makedirs(SAVE_FOLDER, exist_ok=True)

def send_telegram_photo(photo_path, caption=""):
    if not BOT_TOKEN or not CHAT_ID: return
    try:
        with open(photo_path, "rb") as file:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": file}, timeout=15)
    except: pass

def convert_to_16_9(image_path):
    """Magic function to convert 1:1 or 3:2 Bing images to YouTube 16:9 format"""
    print("🎨 Converting image to 1920x1080 (16:9) with Blurred Background...")
    try:
        img = Image.open(image_path).convert("RGB")
        
        # 1. Create a 1920x1080 background by resizing and heavy blurring
        bg = img.resize((1920, 1080), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(40)) # Heavy blur
        
        # 2. Resize the original image to fit the height (1080) perfectly
        orig_width, orig_height = img.size
        new_height = 1080
        new_width = int((new_height / orig_height) * orig_width)
        fg = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 3. Paste the original image in the exact center
        offset_x = (1920 - new_width) // 2
        bg.paste(fg, (offset_x, 0))
        
        # 4. Save the masterpiece
        bg.save(image_path, format="JPEG", quality=95)
        print("✅ Image successfully converted to 16:9 Cinematic Ratio!")
    except Exception as e:
        print(f"⚠️ Failed to convert image to 16:9: {e}")

async def generate_single_image(machine_id, prompt_text):
    out_img_path = os.path.join(SAVE_FOLDER, f"scene_{machine_id}.jpg")
    clean_prompt = re.sub(r'--ar\s+\d+:\d+', '', prompt_text).strip()
    
    max_retries = 5

    async with async_playwright() as p:
        for attempt in range(1, max_retries + 1):
            print(f"\n🔄 [Attempt {attempt}/{max_retries}] Opening Browser for Scene {machine_id}...")
            
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width': 1280, 'height': 720})
            page = await context.new_page()
            
            try:
                await page.goto("https://www.bing.com/images/create", timeout=60000)
                await asyncio.sleep(3)
                
                await page.locator("textarea, input[placeholder*='Describe']").first.fill(clean_prompt)
                await asyncio.sleep(1)
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
                
                # Apply the 16:9 Fix directly after downloading!
                convert_to_16_9(out_img_path)
                
                send_telegram_photo(out_img_path, f"✅ [Scene {machine_id}] 16:9 Image Created Successfully!")
                return True
                
            except Exception as e:
                print(f"⚠️ Error on Attempt {attempt}: {str(e)[:50]}... Retrying!")
                await browser.close()
                await asyncio.sleep(4)
                
        print(f"❌ All {max_retries} attempts FAILED for Scene {machine_id}.")
        return False

async def main():
    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    prompts = {}
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f.readlines(), 1):
                parts = line.strip().split("|")
                if len(parts) >= 2:
                    prompts[idx] = parts[1].strip() # 2nd Part is the Image Prompt
                    
    await generate_single_image(machine_id, prompts.get(machine_id, "A cinematic wide shot landscape"))

if __name__ == "__main__":
    asyncio.run(main())
