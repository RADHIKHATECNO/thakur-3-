import asyncio
import os
import sys
import time
import requests
from playwright.async_api import async_playwright

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

VIDEO_DIR = "generated_videos"
os.makedirs(VIDEO_DIR, exist_ok=True)

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
    except:
        pass

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
    except:
        pass

async def live_screenshot_monitor(page, machine_id, stop_event):
    shot_count = 1
    while not stop_event.is_set():
        await asyncio.sleep(25)
        if stop_event.is_set():
            break
        try:
            shot_path = os.path.join(VIDEO_DIR, f"live_m{machine_id}.png")
            await page.screenshot(path=shot_path, timeout=5000)
            send_telegram_photo(shot_path, f"🎬 [M-{machine_id}] Status #{shot_count}")
            shot_count += 1
        except:
            pass

def read_video_prompts():
    if not os.path.exists("prompts.txt"):
        return {}
    with open("prompts.txt", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Prompts ab ### se separated hain (new format)
    raw_prompts = content.split("\n\n")  # double newline se split (kyunki humne join("\n\n") kiya tha)
    video_prompts = {}
    for idx, prompt in enumerate(raw_prompts, start=1):
        prompt = prompt.strip()
        if len(prompt) > 30:  # Valid prompt check
            video_prompts[idx] = prompt
    return video_prompts


async def main():
    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    video_prompts = read_video_prompts()

    text_prompt = video_prompts.get(machine_id, "A cinematic 5-second video of nature")
    print(f"🖥️ Machine {machine_id} - Direct TEXT-TO-VIDEO Generation")
    print(f"📝 Prompt: {text_prompt[:80]}...")

    async with async_playwright() as p:
        max_attempts = 10

        for attempt in range(1, max_attempts + 1):
            print(f"\n🔄 [Attempt {attempt}/{max_attempts}] Fresh Browser...")

            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(accept_downloads=True, viewport={'width': 1280, 'height': 720})
            page = await context.new_page()

            stop_tracker = asyncio.Event()
            asyncio.create_task(live_screenshot_monitor(page, machine_id, stop_tracker))

            try:
                await page.goto("https://upsampler.com/free-video-generator-no-signup", wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)

                # Accept cookies if present
                try:
                    accept_btn = page.get_by_role("button", name="Accept")
                    if await accept_btn.is_visible(timeout=3000):
                        await accept_btn.click()
                except:
                    pass

                # 🔴 TEXT PROMPT ENTRY (NO IMAGE UPLOAD)
                print("📝 Entering text prompt...")
                selectors = [
                    "textarea[placeholder*='prompt' i]",
                    "input[placeholder*='prompt' i]",
                    "textarea[placeholder*='Describe' i]",
                    "input[placeholder*='Describe' i]",
                    "textarea"
                ]
                for sel in selectors:
                    loc = page.locator(sel).first
                    try:
                        if await loc.is_visible(timeout=2000):
                            await loc.fill(text_prompt)
                            print("✅ Prompt entered!")
                            break
                    except:
                        continue

                # Select 5 seconds duration
                try:
                    duration_dropdown = page.get_by_text("3 seconds")
                    if await duration_dropdown.is_visible(timeout=3000):
                        await duration_dropdown.click()
                        await asyncio.sleep(1)
                        await page.get_by_text("5 seconds", exact=True).click()
                        print("⏳ 5 seconds selected!")
                except:
                    pass

                # Generate button
                generate_btn = page.get_by_role("button", name="Generate Video", exact=True)
                if not await generate_btn.is_visible(timeout=3000):
                    generate_btn = page.locator("button:has-text('Generate')").first

                if await generate_btn.is_visible():
                    await generate_btn.click()
                    print("🎬 Generation started...")

                await asyncio.sleep(8)

                # Check for errors
                gpu_error = page.get_by_text("free GPUs are in high demand", exact=False)
                ip_limit_error = page.get_by_text("used up today", exact=False)

                if await ip_limit_error.is_visible() or await gpu_error.is_visible():
                    print(f"⚠️ Limit/GPU error! Retry {attempt}...")
                    stop_tracker.set()
                    await browser.close()
                    await asyncio.sleep(5)
                    continue

                print("✅ Waiting up to 6 minutes for video...")
                see_result_btn = page.locator("button:has-text('See result'), a:has-text('See result')").first
                video_element = page.locator("video:not([src*='_static'])").first

                start_time = time.time()
                video_ready = False

                while time.time() - start_time < 360:
                    await asyncio.sleep(5)

                    if await ip_limit_error.is_visible() or await gpu_error.is_visible():
                        print("⚠️ Error during wait! Restarting...")
                        break

                    if await see_result_btn.is_visible():
                        await see_result_btn.click()
                        await asyncio.sleep(2)

                    if await video_element.count() > 0 and await video_element.is_visible():
                        video_ready = True
                        break

                if video_ready:
                    stop_tracker.set()
                    await asyncio.sleep(2)

                    pre_shot = os.path.join(VIDEO_DIR, f"pre_m{machine_id}.png")
                    await page.screenshot(path=pre_shot)
                    send_telegram_photo(pre_shot, f"📸 Video {machine_id} Preview!")
                    await asyncio.sleep(4)

                    video_filename = os.path.join(VIDEO_DIR, f"video_{machine_id}.mp4")
                    video_src = await video_element.get_attribute("src")

                    if video_src:
                        download_btn = page.locator("a:has-text('Download'), button:has-text('Download')").first
                        if await download_btn.is_visible():
                            async with page.expect_download() as download_info:
                                await download_btn.click()
                            download = await download_info.value
                            await download.save_as(video_filename)
                        else:
                            v_data = requests.get(video_src).content
                            with open(video_filename, "wb") as f:
                                f.write(v_data)

                        print(f"🎉 Video {machine_id} Downloaded!")
                        send_telegram_video(video_filename, f"🎬 Scene {machine_id} Ready!")

                        await browser.close()
                        return

            except Exception as e:
                print(f"⚠️ Error: {e}. Restarting...")

            stop_tracker.set()
            await browser.close()
            await asyncio.sleep(5)

        print(f"❌ Failed after {max_attempts} attempts for video {machine_id}.")


if __name__ == "__main__":
    asyncio.run(main())
