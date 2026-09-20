import os
import re
import json
import base64
import googleapiclient.discovery
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

# ============================================================
# CONFIG
# ============================================================
VIDEO_FILE  = "final_output/Final_4K_Monetizable_Short.mp4"
META_FILE   = "metadata.txt"
CONFIG_FILE = "video_config.json"

# ============================================================
# CONFIG LOADER
# ============================================================
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "video_type": "short",
        "aspect_ratio": "9:16"
    }

# ============================================================
# TOKEN GENERATOR
# ============================================================
def create_token_from_secret():
    token_b64 = os.getenv("YOUTUBE_TOKEN_BASE64")
    if token_b64:
        try:
            token_json_str = base64.b64decode(token_b64).decode("utf-8")
            with open("token.json", "w") as f:
                f.write(token_json_str)
            print("✅ token.json generated from secret!")
        except Exception as e:
            print(f"❌ Token decode failed: {e}")
    else:
        print("⚠️ YOUTUBE_TOKEN_BASE64 not found!")

# ============================================================
# METADATA PARSER
# ============================================================
def parse_metadata(config):
    """
    metadata.txt se title, desc, tags lo
    Short aur Long ke liye alag style
    """
    video_type   = config.get("video_type", "short")
    aspect_ratio = config.get("aspect_ratio", "9:16")

    # Defaults
    if video_type == "short":
        default_title = "😂 Funny Story Jo Aapko Hasaegi! #shorts"
        default_desc  = (
            "Ek mazedaar kahani jo aapko hasaegi!\n"
            "Subscribe karo aur bell icon dabao! 🔔\n"
            "#shorts #funny #comedy #hindi"
        )
        default_tags = [
            "shorts", "funny", "comedy", "hindi shorts",
            "viral shorts", "funny story", "hindi comedy",
            "cartoon story", "animated story", "trending shorts"
        ]
    else:
        default_title = "😂 Ek Mazedaar Kahani Jo Aapko Rona Hasaegi!"
        default_desc  = (
            "Aaj ki kahani bahut hi mazedaar hai!\n"
            "Poori video dekho aur batao kaisi lagi!\n"
            "Subscribe karo channel ko! 🔔\n\n"
            "#funny #comedy #hindi #story #viral"
        )
        default_tags = [
            "funny story", "hindi comedy", "viral video",
            "animated story", "cartoon", "comedy video",
            "hindi story", "funny cartoon", "entertainment",
            "trending", "viral", "comedy shorts"
        ]

    title = default_title
    desc  = default_desc
    tags  = default_tags

    if os.path.exists(META_FILE):
        with open(META_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        try:
            # Title
            title_match = re.search(r"TITLE:\s*(.*)", content)
            if title_match:
                title = title_match.group(1).strip()

                # Shorts ke liye #shorts add karo
                if video_type == "short" and "#shorts" not in title.lower():
                    title = title[:50] + " #shorts"

            # Description
            desc_match = re.search(
                r"DESC:\s*([\s\S]*?)(?:TAGS:|VIDEO_TYPE:|$)",
                content
            )
            if desc_match:
                desc = desc_match.group(1).strip()

            # Tags
            tags_match = re.search(r"TAGS:\s*(.*)", content)
            if tags_match:
                tags_str = tags_match.group(1).strip()
                tags = [t.strip() for t in tags_str.split(",") if t.strip()]

                # Shorts ke liye extra tags
                if video_type == "short":
                    extra = ["shorts", "ytshorts", "shortsviral", "trending"]
                    for t in extra:
                        if t not in tags:
                            tags.append(t)

                tags = tags[:15]  # Max 15 tags

        except Exception as e:
            print(f"⚠️ Metadata parse error: {e}. Using defaults.")

    # AI disclaimer add karo description mein
    ai_disclaimer = (
        "⚠️ Disclaimer: Yeh ek creative AI-assisted story hai. "
        "Visuals aur voice AI tools se banaye gaye hain.\n\n"
    )
    final_desc = ai_disclaimer + desc

    # Subscribe CTA add karo
    cta = (
        "\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔔 Subscribe karo aur bell icon dabao!\n"
        "👍 Like karo agar achha laga!\n"
        "💬 Comment mein batao kaisi lagi kahani!\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    final_desc = final_desc + cta

    return title, final_desc, tags

# ============================================================
# THUMBNAIL GENERATOR (Auto)
# ============================================================
def create_thumbnail():
    """
    Video ke pehle frame se thumbnail banao
    """
    thumb_path = "thumbnail.jpg"
    try:
        import subprocess
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", VIDEO_FILE,
                "-ss", "00:00:02",      # 2 second pe frame lo
                "-vframes", "1",
                "-vf", "scale=1280:720",
                thumb_path
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ Thumbnail created!")
        return thumb_path
    except Exception as e:
        print(f"⚠️ Thumbnail creation failed: {e}")
        return None

# ============================================================
# YOUTUBE UPLOADER
# ============================================================
def upload_video():
    print("\n" + "="*50)
    print("🚀 YOUTUBE AUTO UPLOADER")
    print("="*50 + "\n")

    # Video check
    if not os.path.exists(VIDEO_FILE):
        print(f"❌ Video not found: {VIDEO_FILE}")
        return

    video_size = os.path.getsize(VIDEO_FILE) / (1024 * 1024)
    print(f"📁 Video Size: {video_size:.1f} MB")

    # Token banao
    create_token_from_secret()

    if not os.path.exists("token.json"):
        print("❌ token.json missing! Upload failed.")
        return

    # Config load karo
    config = load_config()
    video_type = config.get("video_type", "short")

    print(f"📺 Video Type: {video_type.upper()}")

    # Metadata lo
    title, desc, tags = parse_metadata(config)

    print(f"\n📌 Title : {title}")
    print(f"🏷️  Tags  : {', '.join(tags[:5])}...")

    # YouTube connect karo
    try:
        creds = Credentials.from_authorized_user_file(
            "token.json",
            ["https://www.googleapis.com/auth/youtube.upload"]
        )
        youtube = googleapiclient.discovery.build(
            "youtube", "v3",
            credentials=creds
        )
    except Exception as e:
        print(f"❌ YouTube auth failed: {e}")
        return

    # Video metadata
    # Shorts ke liye category 24 (Entertainment)
    # Long ke liye bhi 24
    request_body = {
        "snippet": {
            "categoryId": "24",
            "title": title[:100],
            "description": desc[:5000],
            "tags": tags,
            "defaultLanguage": "hi",
            "defaultAudioLanguage": "hi"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids": False
        }
    }

    # Shorts ke liye extra settings
    if video_type == "short":
        request_body["snippet"]["title"] = (
            title[:90] + " #shorts"
            if "#shorts" not in title
            else title[:100]
        )

    # Upload start karo
    print("\n⏳ Uploading to YouTube...")
    media_file = MediaFileUpload(
        VIDEO_FILE,
        chunksize=1024*1024,  # 1MB chunks
        resumable=True,
        mimetype="video/mp4"
    )

    try:
        request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media_file
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"   📤 Upload Progress: {progress}%")

        video_id  = response["id"]
        video_url = f"https://youtu.be/{video_id}"

        print(f"\n{'='*50}")
        print(f"🎉 VIDEO UPLOADED SUCCESSFULLY!")
        print(f"   🔗 URL      : {video_url}")
        print(f"   📺 Type     : {video_type.upper()}")
        print(f"   📌 Title    : {title}")
        print(f"{'='*50}\n")

        # Thumbnail set karo
        thumb_path = create_thumbnail()
        if thumb_path:
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumb_path)
                ).execute()
                print("✅ Thumbnail uploaded!")
            except Exception as e:
                print(f"⚠️ Thumbnail upload failed: {e}")

        # Video ID save karo (reference ke liye)
        with open("last_upload.txt", "w") as f:
            f.write(f"video_id={video_id}\n")
            f.write(f"url={video_url}\n")
            f.write(f"title={title}\n")

    except Exception as e:
        print(f"❌ Upload Failed: {e}")

if __name__ == "__main__":
    upload_video()
