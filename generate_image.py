import sys
import os
import asyncio
import re
from playwright.async_api import async_playwright
from PIL import Image, ImageFilter

SAVE_FOLDER = "scene_images"
PROMPT_FILE = "prompts.txt"
os.makedirs(SAVE_FOLDER, exist_ok=True)

def convert_to_16_9(image_path):
    print("🎨 Converting image to 1920x1080 (16:9 Cinematic)...")
    try:
        img = Image.open(image_path).convert("RGB")
        # Background Blur Layer
        bg = img.resize((1920, 1080), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(50))
        
        # Foreground Sharp Image Layer
        orig_w, orig_h = img.size
        new_h = 1080
        new_w = int((new_h / orig_h) * orig_w)
        fg = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Merge
        offset_x = (1920 - new_w) // 2
        bg.paste(fg, (offset_x, 0))
        
        bg.save(image_path, format="JPEG", quality=98)
        print("✅ 16:9 Format Ready!")
    except Exception as e:
        print(f"⚠️ Failed 16:9 conversion: {e}")

async def generate_single_image(machine_id, prompt_text):
    out_img_path = os.path.join(SAVE_FOLDER, f"scene_{machine_id}.jpg")
    clean_prompt = re.sub(r'--ar\s+\d+:\d+', '', prompt_text).strip()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto("https://www.bing.com/images/create", timeout=60000)
            await asyncio.sleep(2)
            await page.locator("textarea, input[placeholder*='Describe']").first.fill(clean_prompt)
            await page.locator("button:has-text('Generate'), button:has-text('Create')").first.click()
            
            print("⏳ Generating Image on Bing...")
            download_btn = page.locator("a:has-text('Download'), button[title='Download']:not([disabled])").first
            await download_btn.wait_for(state="visible", timeout=90000)
            
            async with page.expect_download() as download_info:
                await download_btn.click()
                download = await download_info.value
                await download.save_as(out_img_path)
                
            convert_to_16_9(out_img_path)
            return True
        except Exception as e:
            print(f"❌ Failed Image {machine_id}: {str(e)[:50]}")
        finally:
            await browser.close()
    return False

async def main():
    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if machine_id <= len(lines):
                prompt = lines[machine_id - 1].split("|")[1].strip()
                await generate_single_image(machine_id, prompt)

if __name__ == "__main__":
    asyncio.run(main())
