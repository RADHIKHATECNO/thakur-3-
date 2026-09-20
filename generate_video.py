import asyncio
import os
import sys
import json
import time
import requests
from playwright.async_api import async_playwright

# ============================================================
# CONFIG
# ============================================================
BOT_TOKEN  = os.getenv("BOT_TOKEN", "")
CHAT_ID    = os.getenv("CHAT_ID", "")
IMAGE_DIR  = "scene_images"
VIDEO_DIR  = "generated_videos"
CONFIG_FILE = "video_config.json"
PROMPT_FILE = "prompts.txt"

os.makedirs(VIDEO_DIR, exist_ok=True)

# ============================================================
# CONFIG LOADER
# ============================================================
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "video_type": "short",
        "duration_sec": 30,
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
        if os.path.exists(photo_path):
            with open(photo_path, "rb") as file:
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={"chat_id": CHAT_ID, "caption": caption},
                    files={"photo": file},
                    timeout=20
                )
    except Exception as e:
        print(f"⚠️ Telegram photo error: {e}")

def send_telegram_video(video_path, caption=""):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        if os.path.exists(video_path):
            with open(video_path, "rb") as file:
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo",
                    data={"chat_id": CHAT_ID, "caption": caption},
                    files={"video": file},
                    timeout=120
                )
    except Exception as e:
        print(f"⚠️ Telegram video error: {e}")

# ============================================================
# LIVE SCREENSHOT MONITOR
# ============================================================
async def live_screenshot_monitor(page, machine_id, stop_event):
    shot_count = 1
    while not stop_event.is_set():
        await asyncio.sleep(25)
        if stop_event.is_set():
            break
        try:
            shot_path = os.path.join(VIDEO_DIR, f"live_video_m{machine_id}.png")
            await page.screenshot(path=shot_path, timeout=5000)
            send_telegram_photo(
                shot_path,
                f"🎬 [Machine {machine_id}] Video Status #{shot_count}"
            )
            shot_count += 1
            print(f"📸 Live Screenshot #{shot_count-1} - Machine {machine_id}")
        except Exception as e:
            print(f"⚠️ Screenshot failed: {e}")

# ============================================================
# PROMPT READER
# ============================================================
def read_video_prompts(config):
    """
    prompts.txt se video motion prompts nikalo
    Character consistency add karo
    """
    if not os.path.exists(PROMPT_FILE):
        return {}

    character = config.get("character", "")
    video_type = config.get("video_type", "short")

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    video_prompts = {}
    for idx, line in enumerate(lines, start=1):
        if "|" in line:
            # Part 1 = visual, Part 2 = narration
            visual = line.split("|")[0].strip()
        else:
            visual = line.strip()

        # Motion prompt enhance karo
        if video_type == "short":
            motion_style = (
                "smooth cinematic camera movement, "
                "funny expressive animation, "
                "bright colorful scene, "
                "energetic motion"
            )
        else:
            motion_style = (
                "slow cinematic pan, "
                "detailed environment, "
                "smooth professional camera work, "
                "storytelling motion"
            )

        enhanced_prompt = (
            f"{visual}. "
            f"Character: {character}. "
            f"{motion_style}. "
            f"Foley sound effects only. "
            f"NO BGM. NO VOICE."
        )

        video_prompts[idx] = enhanced_prompt

    return video_prompts

# ============================================================
# CLIP DURATION CALCULATOR
# ============================================================
def get_clip_duration(machine_id):
    """
    Timing map se is scene ki voice duration lo
    Video utni hi lambi banegi jitni voice hai
    """
    timing_map_path = "timing_map.json"
    default_duration = 5  # Default 5 seconds

    if not os.path.exists(timing_map_path):
        return default_duration

    try:
        with open(timing_map_path, "r") as f:
            timing_map = json.load(f)

        scene_key = str(machine_id)
        if scene_key in timing_map:
            duration = timing_map[scene_key].get("duration_sec", default_duration)
            # Minimum 3 sec, Maximum 15 sec per clip
            duration = max(3.0, min(15.0, float(duration)))
            print(f"⏱️  Scene {machine_id} duration: {duration}s (from voice)")
            return duration
    except Exception as e:
        print(f"⚠️ Timing map read error: {e}")

    return default_duration

# ============================================================
# VIDEO GENERATOR - UPSAMPLER
# ============================================================
async def generate_video_upsampler(machine_id, img_path, motion_prompt, duration):
    """
    Upsampler.com se image to video generate karo
    10 browser restarts tak try karega
    """
    video_filename = os.path.join(VIDEO_DIR, f"video_{machine_id}.mp4")

    # Pehle se bana hai toh skip
    if os.path.exists(video_filename) and os.path.getsize(video_filename) > 10000:
        print(f"⏭️  Video {machine_id} already exists. Skipping.")
        return True

    async with async_playwright() as p:
        max_restarts = 10

        for attempt in range(1, max_restarts + 1):
            print(f"\n🔄 [Attempt {attempt}/{max_restarts}] Scene {machine_id}...")

            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                accept_downloads=True,
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()

            stop_tracker = asyncio.Event()
            asyncio.create_task(
                live_screenshot_monitor(page, machine_id, stop_tracker)
            )

            try:
                # Site open karo
                await page.goto(
                    "https://upsampler.com/free-video-generator-no-signup",
                    wait_until="domcontentloaded",
                    timeout=60000
                )
                await asyncio.sleep(3)

                # Cookie accept
                try:
                    accept_btn = page.get_by_role("button", name="Accept")
                    if await accept_btn.is_visible(timeout=3000):
                        await accept_btn.click()
                        print("✅ Cookie accepted")
                except:
                    pass

                # Image upload
                file_input = page.locator("input[type='file']").first
                await file_input.set_input_files(img_path)
                await asyncio.sleep(3)
                print("✅ Image uploaded")

                # Motion prompt fill karo
                prompt_selectors = [
                    "input[placeholder*='prompt' i]",
                    "textarea[placeholder*='prompt' i]",
                    "input[placeholder*='Describe' i]",
                    "textarea[placeholder*='Describe' i]",
                    "textarea"
                ]
                for sel in prompt_selectors:
                    loc = page.locator(sel).first
                    try:
                        if await loc.is_visible(timeout=2000):
                            await loc.fill(motion_prompt)
                            print("✅ Prompt filled")
                            break
                    except:
                        continue

                # Duration select karo (5 seconds best for shorts)
                try:
                    duration_text = page.get_by_text("3 seconds")
                    if await duration_text.is_visible(timeout=3000):
                        await duration_text.click()
                        await asyncio.sleep(1)
                        await page.get_by_text("5 seconds", exact=True).click()
                        print("✅ 5 seconds duration selected")
                except:
                    pass

                # Generate button click
                generate_btn = page.get_by_role(
                    "button", name="Generate Video", exact=True
                )
                if not await generate_btn.is_visible(timeout=3000):
                    generate_btn = page.locator(
                        "button:has-text('Generate')"
                    ).first

                if await generate_btn.is_visible():
                    await generate_btn.click()
                    print("✅ Generation started!")

                await asyncio.sleep(8)

                # Error check
                gpu_error   = page.get_by_text("free GPUs are in high demand", exact=False)
                limit_error = page.get_by_text("used up today", exact=False)

                if await limit_error.is_visible() or await gpu_error.is_visible():
                    print(f"⚠️  Limit/GPU error! Restarting browser...")
                    stop_tracker.set()
                    await browser.close()
                    await asyncio.sleep(5)
                    continue

                # Video ready hone ka wait (max 6 min)
                print("⏳ Waiting for video (max 6 minutes)...")
                see_result_btn = page.locator(
                    "button:has-text('See result'), a:has-text('See result')"
                ).first
                video_element = page.locator(
                    "video:not([src*='_static'])"
                ).first

                start_time  = time.time()
                video_ready = False

                while time.time() - start_time < 360:
                    await asyncio.sleep(5)

                    # Error check during wait
                    if (await limit_error.is_visible() or
                            await gpu_error.is_visible()):
                        print("⚠️  Error during wait! Restarting...")
                        break

                    # See result button click
                    try:
                        if await see_result_btn.is_visible():
                            await see_result_btn.click()
                            await asyncio.sleep(2)
                    except:
                        pass

                    # Video ready check
                    if (await video_element.count() > 0 and
                            await video_element.is_visible()):
                        video_ready = True
                        break

                if not video_ready:
                    print(f"⚠️  Video not ready. Restarting browser...")
                    stop_tracker.set()
                    await browser.close()
                    await asyncio.sleep(5)
                    continue

                # ✅ Video ready - Download karo
                stop_tracker.set()
                await asyncio.sleep(2)

                # Preview screenshot
                preview_path = os.path.join(
                    VIDEO_DIR, f"preview_m{machine_id}.png"
                )
                await page.screenshot(path=preview_path)
                send_telegram_photo(
                    preview_path,
                    f"📸 Scene {machine_id} ready! Downloading..."
                )
                await asyncio.sleep(4)

                # Download logic
                video_src = await video_element.get_attribute("src")

                if video_src:
                    download_btn = page.locator(
                        "a:has-text('Download'), button:has-text('Download')"
                    ).first

                    if await download_btn.is_visible():
                        async with page.expect_download() as dl_info:
                            await download_btn.click()
                        download = await dl_info.value
                        await download.save_as(video_filename)
                    else:
                        # Direct download fallback
                        video_data = requests.get(video_src, timeout=60).content
                        with open(video_filename, "wb") as f:
                            f.write(video_data)

                print(f"🎉 Scene {machine_id} video downloaded!")
                send_telegram_video(
                    video_filename,
                    f"🎬 Scene {machine_id} Final Video Ready!"
                )

                await browser.close()
                return True

            except Exception as e:
                print(f"⚠️  Crash on attempt {attempt}: {e}")
                stop_tracker.set()
                await browser.close()
                await asyncio.sleep(5)

        print(f"❌ All {max_restarts} attempts failed for Scene {machine_id}!")
        return False

# ============================================================
# MAIN
# ============================================================
async def main():
    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    # Config load karo
    config = load_config()

    print(f"\n{'='*50}")
    print(f"🎬 VIDEO GENERATOR - Scene {machine_id}")
    print(f"   Type     : {config.get('video_type', 'short').upper()}")
    print(f"   Ratio    : {config.get('aspect_ratio', '9:16')}")
    print(f"{'='*50}\n")

    # Image path
    img_path = os.path.join(IMAGE_DIR, f"scene_{machine_id}.jpg")
    if not os.path.exists(img_path):
        print(f"❌ Image not found: {img_path}")
        return

    # Video prompts lo
    video_prompts = read_video_prompts(config)
    motion_prompt = video_prompts.get(
        machine_id,
        "Smooth cinematic movement, funny cartoon style, bright colors"
    )

    # Voice duration se clip length lo
    clip_duration = get_clip_duration(machine_id)
    print(f"⏱️  Clip Duration: {clip_duration}s")

    # Video generate karo
    await generate_video_upsampler(
        machine_id,
        img_path,
        motion_prompt,
        clip_duration
    )

if __name__ == "__main__":
    asyncio.run(main())
