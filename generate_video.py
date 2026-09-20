import asyncio
import os
import sys
import time
import requests
from playwright.async_api import async_playwright

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

IMAGE_DIR = "scene_images"
VIDEO_DIR = "generated_videos"
os.makedirs(VIDEO_DIR, exist_ok=True)

def send_telegram_photo(photo_path, caption=""):
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        if os.path.exists(photo_path):
            with open(photo_path, "rb") as file:
                requests.post(
                    url,
                    data={"chat_id": CHAT_ID, "caption": caption},
                    files={"photo": file},
                    timeout=20
                )
    except Exception as e:
        print(f"⚠️ Telegram photo error: {e}")

def send_telegram_video(video_path, caption=""):
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    try:
        if os.path.exists(video_path):
            with open(video_path, "rb") as file:
                requests.post(
                    url,
                    data={"chat_id": CHAT_ID, "caption": caption},
                    files={"video": file},
                    timeout=120
                )
    except Exception as e:
        print(f"⚠️ Telegram video error: {e}")

def read_video_prompts():
    """
    prompts.txt से Video Motion Prompt पढ़ो
    Format: [Image Prompt] | [Video Motion Prompt] | [Dialogue]
    हमें दूसरा हिस्सा (index 1) चाहिए
    """
    if not os.path.exists("prompts.txt"):
        return {}
    with open("prompts.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

    video_prompts = {}
    for idx, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) >= 2:
            # दूसरा हिस्सा = Video Motion Prompt (Upsampler के लिए)
            video_prompts[idx] = parts[1].strip()
        else:
            video_prompts[idx] = "Cinematic slow motion movement, smooth camera pan"
    return video_prompts

async def live_screenshot_monitor(page, machine_id, stop_event):
    """हर 25 सेकंड में Telegram पर Live Status Screenshot भेजो"""
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
                f"🎬 [Machine {machine_id}] Upsampler Status #{shot_count}"
            )
            shot_count += 1
            print(f"📸 Live Screenshot #{shot_count-1} sent for Machine {machine_id}")
        except Exception as e:
            print(f"⚠️ Screenshot failed (page loading): {e}")

async def generate_video(machine_id):
    video_prompts = read_video_prompts()

    img_path = os.path.join(IMAGE_DIR, f"scene_{machine_id}.jpg")
    if not os.path.exists(img_path):
        print(f"❌ Image not found: {img_path}")
        return False

    motion_prompt = video_prompts.get(
        machine_id,
        "Cinematic slow motion, smooth camera movement, professional cinematography"
    )
    print(f"\n🎬 Machine {machine_id} Starting...")
    print(f"📝 Motion Prompt: {motion_prompt}")

    async with async_playwright() as p:
        max_attempts = 10

        for attempt in range(1, max_attempts + 1):
            print(f"\n🔄 [Attempt {attempt}/{max_attempts}] Opening Fresh Browser...")

            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                accept_downloads=True,
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()

            stop_tracker = asyncio.Event()
            asyncio.create_task(live_screenshot_monitor(page, machine_id, stop_tracker))

            try:
                # Upsampler Website खोलो
                await page.goto(
                    "https://upsampler.com/free-video-generator-no-signup",
                    wait_until="domcontentloaded",
                    timeout=60000
                )
                await asyncio.sleep(3)

                # Cookie Accept करो
                try:
                    accept_btn = page.get_by_role("button", name="Accept")
                    if await accept_btn.is_visible(timeout=3000):
                        await accept_btn.click()
                        print("✅ Cookie accepted")
                except Exception:
                    pass

                # Image Upload करो
                print("📤 Uploading image...")
                file_input = page.locator("input[type='file']").first
                await file_input.set_input_files(img_path)
                await asyncio.sleep(3)

                # Motion Prompt डालो
                print("✍️ Entering motion prompt...")
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
                            print(f"✅ Prompt entered using: {sel}")
                            break
                    except Exception:
                        continue

                # Duration 5 Seconds Select करो
                try:
                    duration_dropdown = page.get_by_text("3 seconds")
                    if await duration_dropdown.is_visible(timeout=3000):
                        await duration_dropdown.click()
                        await asyncio.sleep(1)
                        await page.get_by_text("5 seconds", exact=True).click()
                        print("⏱️ Duration: 5 seconds selected")
                except Exception:
                    print("⚠️ Duration selector not found, using default")

                # Generate Button दबाओ
                print("🚀 Clicking Generate...")
                generate_btn = page.get_by_role("button", name="Generate Video", exact=True)
                if not await generate_btn.is_visible(timeout=3000):
                    generate_btn = page.locator("button:has-text('Generate')").first

                if await generate_btn.is_visible():
                    await generate_btn.click()

                await asyncio.sleep(8)

                # Limit Check करो
                gpu_error = page.get_by_text("free GPUs are in high demand", exact=False)
                ip_limit = page.get_by_text("used up today", exact=False)

                if await ip_limit.is_visible() or await gpu_error.is_visible():
                    print(f"⚠️ Limit/GPU Error! Restarting browser...")
                    stop_tracker.set()
                    await browser.close()
                    await asyncio.sleep(5)
                    continue

                # Video Ready होने का Wait करो (6 मिनट तक)
                print("⏳ Waiting for video generation (up to 6 min)...")
                see_result_btn = page.locator(
                    "button:has-text('See result'), a:has-text('See result')"
                ).first
                video_element = page.locator("video:not([src*='_static'])").first

                start_time = time.time()
                video_ready = False
                limit_hit = False

                while time.time() - start_time < 360:
                    await asyncio.sleep(5)

                    # बार-बार limit check करो
                    if await ip_limit.is_visible() or await gpu_error.is_visible():
                        print("⚠️ Error during wait! Restarting...")
                        limit_hit = True
                        break

                    # See Result button दिखे तो click करो
                    try:
                        if await see_result_btn.is_visible(timeout=1000):
                            await see_result_btn.click()
                            await asyncio.sleep(2)
                    except Exception:
                        pass

                    # Video element दिखे तो रुको
                    try:
                        if await video_element.count() > 0:
                            if await video_element.is_visible(timeout=1000):
                                video_ready = True
                                break
                    except Exception:
                        pass

                if limit_hit:
                    stop_tracker.set()
                    await browser.close()
                    await asyncio.sleep(5)
                    continue

                if video_ready:
                    stop_tracker.set()
                    print("✅ Video generated! Downloading...")
                    await asyncio.sleep(3)

                    # Screenshot लो
                    preview_shot = os.path.join(VIDEO_DIR, f"preview_m{machine_id}.png")
                    await page.screenshot(path=preview_shot)
                    send_telegram_photo(
                        preview_shot,
                        f"✅ Video #{machine_id} Ready! Downloading..."
                    )
                    await asyncio.sleep(2)

                    video_filename = os.path.join(VIDEO_DIR, f"video_{machine_id}.mp4")
                    video_src = await video_element.get_attribute("src")

                    if video_src:
                        # Download Button से Download करो
                        download_btn = page.locator(
                            "a:has-text('Download'), button:has-text('Download')"
                        ).first

                        try:
                            if await download_btn.is_visible(timeout=3000):
                                async with page.expect_download() as download_info:
                                    await download_btn.click()
                                download = await download_info.value
                                await download.save_as(video_filename)
                                print(f"✅ Downloaded via button!")
                            else:
                                # Direct URL से Download करो
                                v_data = requests.get(video_src, timeout=60).content
                                with open(video_filename, "wb") as f:
                                    f.write(v_data)
                                print(f"✅ Downloaded via URL!")
                        except Exception as e:
                            print(f"⚠️ Download button failed: {e}. Trying URL...")
                            v_data = requests.get(video_src, timeout=60).content
                            with open(video_filename, "wb") as f:
                                f.write(v_data)

                        if os.path.exists(video_filename):
                            size = os.path.getsize(video_filename)
                            print(f"🎉 Video #{machine_id} saved! Size: {size/1024:.1f} KB")
                            send_telegram_video(
                                video_filename,
                                f"🎬 Scene #{machine_id} Video Ready!"
                            )
                            await browser.close()
                            return True
                    else:
                        print("⚠️ Video src not found!")

                else:
                    print(f"⏰ Timeout on attempt {attempt}!")

            except Exception as e:
                print(f"⚠️ Browser crashed: {e}")

            stop_tracker.set()
            await browser.close()
            await asyncio.sleep(5)

        print(f"❌ Failed after {max_attempts} attempts for Machine {machine_id}")
        return False

async def main():
    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(f"🚀 Starting Video Generation for Scene {machine_id}")
    success = await generate_video(machine_id)
    if success:
        print(f"🎉 Scene {machine_id} completed successfully!")
    else:
        print(f"❌ Scene {machine_id} failed!")

if __name__ == "__main__":
    asyncio.run(main())
