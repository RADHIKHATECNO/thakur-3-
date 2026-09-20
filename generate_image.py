import sys
import os
import json
import asyncio
import requests
import re
from playwright.async_api import async_playwright

# ============================================================
# CONFIG
# ============================================================
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
CHAT_ID     = os.getenv("CHAT_ID", "")
SAVE_FOLDER = "scene_images"
PROMPT_FILE = "prompts.txt"
CONFIG_FILE = "video_config.json"

os.makedirs(SAVE_FOLDER, exist_ok=True)

# ============================================================
# CONFIG LOADER
# ============================================================
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "video_type"  : "short",
        "aspect_ratio": "9:16",
        "character"   : "",
        "visual_style": "Pixar 3D funny cartoon style"
    }

# ============================================================
# TELEGRAM
# ============================================================
def send_telegram_photo(photo_path, caption=""):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        with open(photo_path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"photo": f},
                timeout=15
            )
    except:
        pass

# ============================================================
# PROMPT EXTRACTOR
# ============================================================
def get_image_prompt(machine_id, config):
    """
    prompts.txt se IMAGE prompt nikalo (Part 2)
    Format: NARRATION >> IMAGE_PROMPT >> VIDEO_PROMPT
    """
    if not os.path.exists(PROMPT_FILE):
        return None

    character    = config.get("character", "")
    char_parts   = character.split("|")
    char_looks   = char_parts[1].strip() if len(char_parts) > 1 else ""
    visual_style = config.get("visual_style", "Pixar 3D funny cartoon style")
    aspect_ratio = config.get("aspect_ratio", "9:16")

    if aspect_ratio == "9:16":
        aspect = "vertical 9:16 composition, mobile format"
    else:
        aspect = "horizontal 16:9 widescreen"

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if machine_id <= len(lines):
        line = lines[machine_id - 1].strip()

        if ">>" in line:
            parts = line.split(">>")
            if len(parts) >= 2:
                img_prompt = parts[1].strip()

                # Enhanced prompt banao
                enhanced = (
                    f"{img_prompt}, "
                    f"character appearance: {char_looks}, "
                    f"style: {visual_style}, "
                    f"{aspect}, "
                    f"bright vivid colors, "
                    f"expressive face, "
                    f"high quality, "
                    f"no text, no watermark"
                )
                return enhanced

    # Fallback
    return (
        f"funny cartoon character in colorful scene, "
        f"{visual_style}, high quality"
    )

# ============================================================
# LIVE TRACKER
# ============================================================
async def live_screenshot_tracker(page, machine_id, stop_event):
    sec = 10
    while not stop_event.is_set():
        await asyncio.sleep(10)
        if stop_event.is_set():
            break
        try:
            shot = os.path.join(SAVE_FOLDER, f"live_{machine_id}.png")
            await page.screenshot(path=shot)
            send_telegram_photo(
                shot,
                f"👀 [Image {machine_id}] {sec}s..."
            )
            sec += 10
        except:
            pass

# ============================================================
# IMAGE GENERATOR
# ============================================================
async def generate_single_image(machine_id, image_prompt):
    out_path    = os.path.join(SAVE_FOLDER, f"scene_{machine_id}.jpg")
    max_retries = 5

    print(f"\n🎨 Scene {machine_id} Image Prompt:")
    print(f"   {image_prompt[:100]}...")

    async with async_playwright() as p:
        for attempt in range(1, max_retries + 1):
            print(f"\n🔄 Attempt {attempt}/{max_retries}...")

            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()

            stop_tracker = asyncio.Event()
            asyncio.create_task(
                live_screenshot_tracker(page, machine_id, stop_tracker)
            )

            try:
                await page.goto(
                    "https://www.bing.com/images/create",
                    timeout=60000
                )
                await asyncio.sleep(3)

                # Prompt fill
                await page.locator(
                    "textarea, input[placeholder*='Describe']"
                ).first.fill(image_prompt)
                await asyncio.sleep(1)

                # Generate click
                await page.locator(
                    "button:has-text('Generate'), "
                    "button:has-text('Create')"
                ).first.click()

                print("⏳ Generating...")

                # Loading wait
                try:
                    await page.locator(
                        "text='We are generating'"
                    ).wait_for(state="detached", timeout=90000)
                except:
                    pass

                # Download button
                dl_btn = page.locator(
                    "button[title='Download']:not([disabled]), "
                    "a:has-text('Download')"
                ).first
                await dl_btn.wait_for(state="visible", timeout=60000)

                print("✅ Done! Waiting 5s for full HD...")
                await asyncio.sleep(5)

                # Download
                async with page.expect_download() as dl_info:
                    await dl_btn.click()

                download = await dl_info.value
                await download.save_as(out_path)

                stop_tracker.set()
                send_telegram_photo(
                    out_path,
                    f"✅ Scene {machine_id} Image Ready! (Attempt {attempt})"
                )

                print(f"🎉 Scene {machine_id} saved!")
                await browser.close()
                return True

            except Exception as e:
                print(f"⚠️ Attempt {attempt} failed: {str(e)[:60]}")
                stop_tracker.set()
                await browser.close()
                await asyncio.sleep(4)

    print(f"❌ All attempts failed for Scene {machine_id}!")
    return False

# ============================================================
# MAIN
# ============================================================
async def main():
    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    config = load_config()

    print(f"\n{'='*50}")
    print(f"🎨 IMAGE GENERATOR - Scene {machine_id}")
    print(f"   Style : {config.get('visual_style', 'Pixar')}")
    print(f"   Ratio : {config.get('aspect_ratio', '9:16')}")
    print(f"{'='*50}\n")

    image_prompt = get_image_prompt(machine_id, config)
    await generate_single_image(machine_id, image_prompt)

if __name__ == "__main__":
    asyncio.run(main())
