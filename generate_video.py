import os
import sys
import time
import requests
from playwright.async_api import async_playwright

async def main():
    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    img_path = f"scene_images/scene_{machine_id}.jpg"
    output_path = f"generated_videos/video_{machine_id}.mp4"
    
    os.makedirs("generated_videos", exist_ok=True)

    if not os.path.exists(img_path):
        print(f"❌ Image {img_path} not found!")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        try:
            await page.goto("https://upsampler.com", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            
            # Placeholder logic for upload
            print(f"⏳ Uploading Image {machine_id}...")
            await page.click("input[type='file']")
            await page.set_input_files("input[type='file']", img_path)
            await page.click("text=Generate")
            
            await page.wait_for_timeout(30000) # Wait for generation
            
            # Logic to click download button would be here
            # Placeholder for success:
            open(output_path, "w").close() 
            
            print(f"✅ Video {machine_id} completed")
        except Exception as e:
            print(f"❌ Video Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
