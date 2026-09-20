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
        "video_type": "short",
        "aspect_ratio": "9:16",
        "character": ""
    }

# ============================================================
# TELEGRAM
# ============================================================
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

# ============================================================
# LIVE SCREENSHOT TRACKER
# ============================================================
async def live_screenshot_tracker(page, machine_id, stop_event):
    sec = 10
    while not stop_event.is_set():
        await asyncio.sleep(10)
        if stop_event.is_set():
            break
        try:
            shot_path = os.path.join(SAVE_FOLDER, f"live_img_m{machine_id}.png")
            await page.screenshot(path=shot_path)
            send_telegram_photo(
                shot_path,
                f"👀 [Image M-{machine_id}] Live: {sec}s..."
            )
            sec += 10
        except:
            pass

# ============================================================
# PROMPT BUILDER
# ============================================================
def build_image_prompt(raw_prompt, character, aspect_ratio, config):
    """
    Visual prompt ko cinematic + character consistent banao
    """
    # Character details add karo
    char_desc = character if character else ""

    # Aspect ratio ke hisaab se style
    if aspect_ratio == "9:16":
        composition = "vertical composition, mobile screen format, 9:16 ratio"
    else:
        composition = "horizontal composition, widescreen format, 16:9 ratio"

    # Clean prompt
    clean = re.sub(r'--ar\s+\d+:\d+', '', raw_prompt).strip()

    # Final enhanced prompt
    enhanced = (
        f"{clean}. "
        f"Main character: {char_desc}. "
        f"Style: bright colorful animation, funny cartoon style, "
        f"expressive faces, vibrant colors, happy mood, "
        f"high quality, {composition}, "
        f"cinematic lighting, no text, no watermark"
    )

    return enhanced

# ============================================================
# IMAGE GENERATOR
# ============================================================
async def generate_single_image(machine_id, prompt_text, character, aspect_ratio):
    out_img_path = os.path.join(SAVE_FOLDER, f"scene_{machine_id}.jpg")

    # Enhanced prompt banao
    enhanced_prompt = build_image_prompt(
        prompt_text, character, aspect_ratio, {}
    )

    print(f"\n🎨 Scene {machine_id} Image Prompt:")
    print(f"   {enhanced_prompt[:100]}...")

    max_retries = 5

    async with async_playwright() as p:
        for attempt in range(1, max_retries + 1):
            print(f"\n🔄 [Attempt {attempt}/{max_retries}] Scene {machine_id}...")

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

                # Prompt fill karo
                await page.locator(
                    "textarea, input[placeholder*='Describe']"
                ).first.fill(enhanced_prompt)
                await asyncio.sleep(1)

                # Generate click
                await page.locator(
                    "button:has-text('Generate'), button:has-text('Create')"
                ).first.click()

                print("⏳ Bing generating image...")

                # Loading hatne ka wait
                try:
                    await page.locator(
                        "text='We are generating'"
                    ).wait_for(state="detached", timeout=90000)
                except:
                    pass

                # Download button wait
                download_btn = page.locator(
                    "button[title='Download']:not([disabled]), a:has-text('Download')"
                ).first
                await download_btn.wait_for(state="visible", timeout=60000)

                # Extra wait for full HD load
                print("✅ Render done! Waiting 5s for full HD...")
                await asyncio.sleep(5)

                # Download
                async with page.expect_download() as download_info:
                    await download_btn.click()

                download = await download_info.value
                await download.save_as(out_img_path)

                stop_tracker.set()
                send_telegram_photo(
                    out_img_path,
                    f"✅ [Scene {machine_id}] Image Ready! Attempt {attempt}"
                )

                print(f"🎉 Scene {machine_id} image saved!")
                await browser.close()
                return True

            except Exception as e:
                print(f"⚠️ Attempt {attempt} failed: {str(e)[:60]}")
                stop_tracker.set()
                await browser.close()
                await asyncio.sleep(4)

        print(f"❌ All {max_retries} attempts failed for Scene {machine_id}!")
        return False

# ============================================================
# MAIN
# ============================================================
async def main():
    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    # Config load karo
    config      = load_config()
    character   = config.get("character", "")
    aspect_ratio = config.get("aspect_ratio", "9:16")

    print(f"\n{'='*50}")
    print(f"🎨 IMAGE GENERATOR - Scene {machine_id}")
    print(f"   Character    : {character[:50]}...")
    print(f"   Aspect Ratio : {aspect_ratio}")
    print(f"{'='*50}\n")

    # Prompts load karo
    prompts = {}
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f.readlines(), 1):
                parts = line.strip().split("|")
                if parts:
                    # Part 1 = visual prompt
                    prompts[idx] = parts[0].strip()

    prompt_text = prompts.get(
        machine_id,
        "A funny colorful cartoon character in a bright happy scene"
    )

    await generate_single_image(
        machine_id, prompt_text, character, aspect_ratio
    )

if __name__ == "__main__":
    asyncio.run(main())
