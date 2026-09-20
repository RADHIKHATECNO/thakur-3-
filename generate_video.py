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
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
CHAT_ID     = os.getenv("CHAT_ID", "")
IMAGE_DIR   = "scene_images"
VIDEO_DIR   = "generated_videos"
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
        "video_type"   : "short",
        "duration_sec" : 30,
        "aspect_ratio" : "9:16",
        "character"    : ""
    }

# ============================================================
# TELEGRAM
# ============================================================
def send_telegram_photo(photo_path, caption=""):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        if os.path.exists(photo_path):
            with open(photo_path, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={"chat_id": CHAT_ID, "caption": caption},
                    files={"photo": f},
                    timeout=20
                )
    except Exception as e:
        print(f"⚠️ Telegram photo error: {e}")

def send_telegram_video(video_path, caption=""):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        if os.path.exists(video_path):
            with open(video_path, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo",
                    data={"chat_id": CHAT_ID, "caption": caption},
                    files={"video": f},
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
            shot_path = os.path.join(
                VIDEO_DIR,
                f"live_video_m{machine_id}.png"
            )
            await page.screenshot(path=shot_path, timeout=5000)
            send_telegram_photo(
                shot_path,
                f"🎬 [Machine {machine_id}] "
                f"Video Status #{shot_count}"
            )
            shot_count += 1
            print(
                f"📸 Screenshot #{shot_count-1} "
                f"- Machine {machine_id}"
            )
        except Exception as e:
            print(f"⚠️ Screenshot failed: {e}")

# ============================================================
# VIDEO PROMPT READER
# ============================================================
def read_video_prompts(config):
    """
    prompts.txt se VIDEO prompt nikalo
    Format: NARRATION >> IMAGE_PROMPT >> VIDEO_PROMPT
    """
    if not os.path.exists(PROMPT_FILE):
        print(f"❌ {PROMPT_FILE} not found!")
        return {}

    character  = config.get("character", "")
    char_parts = character.split("|")
    char_name  = char_parts[0].strip() if len(char_parts) > 0 else "character"
    char_looks = char_parts[1].strip() if len(char_parts) > 1 else ""
    video_type = config.get("video_type", "short")

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    video_prompts = {}

    for idx, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue

        vid_prompt = ""

        if ">>" in line:
            # NEW FORMAT: NARRATION >> IMAGE >> VIDEO
            parts = line.split(">>")
            if len(parts) >= 3:
                vid_prompt = parts[2].strip()
            elif len(parts) == 2:
                vid_prompt = parts[1].strip()

        elif "|" in line:
            # Old format fallback
            parts      = line.split("|")
            vid_prompt = parts[1].strip() if len(parts) > 1 else line

        else:
            vid_prompt = line

        # Motion style
        if video_type == "short":
            motion_add = (
                "smooth cinematic camera movement, "
                "funny expressive animation, "
                "bright colorful scene, "
                "energetic motion"
            )
        else:
            motion_add = (
                "slow cinematic pan, "
                "detailed environment, "
                "smooth professional camera work, "
                "storytelling motion"
            )

        # Final enhanced prompt
        enhanced = (
            f"{vid_prompt}. "
            f"Character: {char_name} - {char_looks[:60]}. "
            f"{motion_add}. "
            f"Foley sound effects only. NO BGM. NO VOICE."
        )

        video_prompts[idx] = enhanced
        print(f"🎬 Scene {idx} prompt: {vid_prompt[:70]}...")

    print(f"\n✅ {len(video_prompts)} video prompts loaded!")
    return video_prompts

# ============================================================
# CLIP DURATION FROM TIMING MAP
# ============================================================
def get_clip_duration(machine_id):
    """
    timing_map.json se voice duration lo
    Video utni hi lambi banegi
    """
    timing_path     = "timing_map.json"
    default_duration = 5.0

    if not os.path.exists(timing_path):
        print(f"⚠️ timing_map.json not found! Using {default_duration}s")
        return default_duration

    try:
        with open(timing_path, "r") as f:
            timing_map = json.load(f)

        scene_key = str(machine_id)
        if scene_key in timing_map:
            duration = float(
                timing_map[scene_key].get(
                    "duration_sec",
                    default_duration
                )
            )
            # Min 3s Max 15s
            duration = max(3.0, min(15.0, duration))
            print(f"⏱️  Scene {machine_id}: {duration}s (from voice)")
            return duration

    except Exception as e:
        print(f"⚠️ Timing map error: {e}")

    return default_duration

# ============================================================
# VIDEO GENERATOR - UPSAMPLER
# ============================================================
async def generate_video_upsampler(
    machine_id,
    img_path,
    motion_prompt,
    duration
):
    """
    Upsampler.com se image to video generate karo
    10 browser restarts tak try karega
    """
    video_filename = os.path.join(
        VIDEO_DIR,
        f"video_{machine_id}.mp4"
    )

    # Already bana hai?
    if (os.path.exists(video_filename) and
            os.path.getsize(video_filename) > 10000):
        print(f"⏭️  Video {machine_id} already exists!")
        return True

    print(f"\n{'='*50}")
    print(f"🎬 Generating Video {machine_id}")
    print(f"   Image  : {img_path}")
    print(f"   Prompt : {motion_prompt[:80]}...")
    print(f"   Length : {duration}s")
    print(f"{'='*50}\n")

    async with async_playwright() as p:
        max_restarts = 10

        for attempt in range(1, max_restarts + 1):
            print(f"\n🔄 [Attempt {attempt}/{max_restarts}]"
                  f" Scene {machine_id}...")

            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                accept_downloads=True,
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()

            # Live monitor start
            stop_tracker = asyncio.Event()
            asyncio.create_task(
                live_screenshot_monitor(
                    page, machine_id, stop_tracker
                )
            )

            try:
                # Site open
                await page.goto(
                    "https://upsampler.com/free-video-generator-no-signup",
                    wait_until="domcontentloaded",
                    timeout=60000
                )
                await asyncio.sleep(3)
                print("✅ Site opened!")

                # Cookie accept
                try:
                    accept_btn = page.get_by_role(
                        "button", name="Accept"
                    )
                    if await accept_btn.is_visible(timeout=3000):
                        await accept_btn.click()
                        print("✅ Cookie accepted!")
                except:
                    pass

                # Image upload
                file_input = page.locator(
                    "input[type='file']"
                ).first
                await file_input.set_input_files(img_path)
                await asyncio.sleep(3)
                print("✅ Image uploaded!")

                # Motion prompt fill
                prompt_selectors = [
                    "input[placeholder*='prompt' i]",
                    "textarea[placeholder*='prompt' i]",
                    "input[placeholder*='Describe' i]",
                    "textarea[placeholder*='Describe' i]",
                    "textarea"
                ]

                prompt_filled = False
                for sel in prompt_selectors:
                    try:
                        loc = page.locator(sel).first
                        if await loc.is_visible(timeout=2000):
                            await loc.fill(motion_prompt)
                            prompt_filled = True
                            print(f"✅ Prompt filled!")
                            break
                    except:
                        continue

                if not prompt_filled:
                    print("⚠️ Could not fill prompt!")

                # Duration select (5 seconds)
                try:
                    dur_btn = page.get_by_text("3 seconds")
                    if await dur_btn.is_visible(timeout=3000):
                        await dur_btn.click()
                        await asyncio.sleep(1)
                        await page.get_by_text(
                            "5 seconds", exact=True
                        ).click()
                        print("✅ 5 seconds selected!")
                except:
                    print("⚠️ Duration selector not found!")

                # Generate click
                generate_btn = page.get_by_role(
                    "button",
                    name="Generate Video",
                    exact=True
                )

                if not await generate_btn.is_visible(timeout=3000):
                    generate_btn = page.locator(
                        "button:has-text('Generate')"
                    ).first

                if await generate_btn.is_visible():
                    await generate_btn.click()
                    print("✅ Generation started!")
                else:
                    print("❌ Generate button not found!")
                    stop_tracker.set()
                    await browser.close()
                    await asyncio.sleep(5)
                    continue

                await asyncio.sleep(8)

                # Error check
                gpu_error   = page.get_by_text(
                    "free GPUs are in high demand",
                    exact=False
                )
                limit_error = page.get_by_text(
                    "used up today",
                    exact=False
                )

                if (await limit_error.is_visible() or
                        await gpu_error.is_visible()):
                    print(
                        f"⚠️ Limit/GPU error! "
                        f"Restarting browser..."
                    )
                    stop_tracker.set()
                    await browser.close()
                    await asyncio.sleep(5)
                    continue

                # Video ready wait (max 6 min)
                print("⏳ Waiting for video (max 6 min)...")

                see_result = page.locator(
                    "button:has-text('See result'), "
                    "a:has-text('See result')"
                ).first

                video_elem = page.locator(
                    "video:not([src*='_static'])"
                ).first

                start_time  = time.time()
                video_ready = False

                while time.time() - start_time < 360:
                    await asyncio.sleep(5)

                    # Error check during wait
                    if (await limit_error.is_visible() or
                            await gpu_error.is_visible()):
                        print("⚠️ Error during wait!")
                        break

                    # See result click
                    try:
                        if await see_result.is_visible():
                            await see_result.click()
                            await asyncio.sleep(2)
                    except:
                        pass

                    # Video ready check
                    try:
                        if (await video_elem.count() > 0 and
                                await video_elem.is_visible()):
                            video_ready = True
                            print("✅ Video is ready!")
                            break
                    except:
                        pass

                    # Progress log
                    elapsed = int(time.time() - start_time)
                    print(f"   ⏳ Waiting... {elapsed}s elapsed")

                if not video_ready:
                    print("⚠️ Video not ready! Restarting...")
                    stop_tracker.set()
                    await browser.close()
                    await asyncio.sleep(5)
                    continue

                # ✅ Video ready - Screenshot
                stop_tracker.set()
                await asyncio.sleep(2)

                preview_path = os.path.join(
                    VIDEO_DIR,
                    f"preview_m{machine_id}.png"
                )
                await page.screenshot(path=preview_path)
                send_telegram_photo(
                    preview_path,
                    f"📸 Scene {machine_id} Ready! Downloading..."
                )
                await asyncio.sleep(4)

                # Download
                video_src = await video_elem.get_attribute("src")

                if video_src:
                    # Method 1: Download button
                    try:
                        dl_btn = page.locator(
                            "a:has-text('Download'), "
                            "button:has-text('Download')"
                        ).first

                        if await dl_btn.is_visible(timeout=5000):
                            async with page.expect_download() as dl_info:
                                await dl_btn.click()
                            download = await dl_info.value
                            await download.save_as(video_filename)
                            print("✅ Downloaded via button!")

                        else:
                            raise Exception("Download button not visible")

                    except:
                        # Method 2: Direct URL download
                        print("⚠️ Button failed! Trying direct download...")
                        try:
                            video_data = requests.get(
                                video_src,
                                timeout=60
                            ).content
                            with open(video_filename, "wb") as f:
                                f.write(video_data)
                            print("✅ Downloaded via direct URL!")
                        except Exception as e:
                            print(f"❌ Direct download failed: {e}")
                            stop_tracker.set()
                            await browser.close()
                            await asyncio.sleep(5)
                            continue

                else:
                    print("❌ No video source found!")
                    stop_tracker.set()
                    await browser.close()
                    await asyncio.sleep(5)
                    continue

                # Verify download
                if (os.path.exists(video_filename) and
                        os.path.getsize(video_filename) > 10000):
                    size_mb = os.path.getsize(video_filename) / (1024*1024)
                    print(f"🎉 Scene {machine_id} downloaded! ({size_mb:.1f}MB)")
                    send_telegram_video(
                        video_filename,
                        f"🎬 Scene {machine_id} Video Ready! ({size_mb:.1f}MB)"
                    )
                    await browser.close()
                    return True
                else:
                    print("❌ Download file too small!")
                    await browser.close()
                    await asyncio.sleep(5)
                    continue

            except Exception as e:
                print(f"⚠️ Crash: {str(e)[:80]}")
                stop_tracker.set()
                await browser.close()
                await asyncio.sleep(5)

        print(
            f"❌ All {max_restarts} attempts failed "
            f"for Scene {machine_id}!"
        )
        return False

# ============================================================
# MAIN
# ============================================================
async def main():
    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    # Config load
    config = load_config()

    print(f"\n{'='*50}")
    print(f"🎬 VIDEO GENERATOR - Scene {machine_id}")
    print(f"   Type     : {config.get('video_type','short').upper()}")
    print(f"   Ratio    : {config.get('aspect_ratio','9:16')}")
    print(f"   Character: {config.get('character','')[:50]}...")
    print(f"{'='*50}\n")

    # Image check
    img_path = os.path.join(IMAGE_DIR, f"scene_{machine_id}.jpg")
    if not os.path.exists(img_path):
        print(f"❌ Image not found: {img_path}")
        # Fallback paths check
        fallbacks = [
            os.path.join(IMAGE_DIR, f"scene_{machine_id}.png"),
            os.path.join(IMAGE_DIR, f"Generated_Image_{machine_id}.jpg"),
        ]
        for fb in fallbacks:
            if os.path.exists(fb):
                img_path = fb
                print(f"✅ Found fallback: {img_path}")
                break
        else:
            print(f"❌ No image found for scene {machine_id}!")
            return

    # Video prompts load
    print("📋 Loading video prompts...")
    video_prompts = read_video_prompts(config)

    motion_prompt = video_prompts.get(
        machine_id,
        (
            "Smooth cinematic movement, "
            "funny cartoon style, "
            "bright colors, "
            "foley sound only, "
            "no bgm, no voice"
        )
    )

    # Voice duration
    clip_duration = get_clip_duration(machine_id)

    print(f"\n📊 Scene {machine_id} Info:")
    print(f"   🖼️  Image  : {img_path}")
    print(f"   🎬 Prompt : {motion_prompt[:80]}...")
    print(f"   ⏱️  Length : {clip_duration}s")

    # Generate!
    success = await generate_video_upsampler(
        machine_id,
        img_path,
        motion_prompt,
        clip_duration
    )

    if success:
        print(f"\n🎉 Scene {machine_id} COMPLETE!")
    else:
        print(f"\n❌ Scene {machine_id} FAILED!")

if __name__ == "__main__":
    asyncio.run(main())
