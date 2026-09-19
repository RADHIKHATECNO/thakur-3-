import os
import re
import json
import base64
import googleapiclient.discovery
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

VIDEO_FILE = "final_output/Final_4K_Monetizable_Long_Video.mp4"
META_FILE = "metadata.txt"
CATEGORY_ID = "24"  # Entertainment

def create_token_from_secret():
    token_b64 = os.getenv("YOUTUBE_TOKEN_BASE64")
    if token_b64:
        try:
            token_json_str = base64.b64decode(token_b64).decode("utf-8")
            with open('token.json', 'w') as f:
                f.write(token_json_str)
            print("✅ token.json created!")
        except Exception as e:
            print(f"❌ Token decode error: {e}")
    else:
        print("⚠️ YOUTUBE_TOKEN_BASE64 missing!")

def parse_metadata():
    title = "Heart Touching Story 😭"
    description = ""
    tags = "story, emotional, viral"
    
    if os.path.exists(META_FILE):
        with open(META_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            try:
                title = re.search(r"TITLE:\s*(.*)", content).group(1).strip()
                desc_match = re.search(r"DESC:\s*([\s\S]*?)TAGS:", content)
                description = desc_match.group(1).strip() if desc_match else ""
                tags = re.search(r"TAGS:\s*(.*)", content).group(1).strip()
            except:
                pass
    return title, description, tags

def upload_video():
    if not os.path.exists(VIDEO_FILE):
        print(f"❌ Video not found: {VIDEO_FILE}")
        return

    create_token_from_secret()

    title, description, tags_string = parse_metadata()
    tags = [tag.strip() for tag in tags_string.split(",")][:15]  # Max 15 for long videos

    ai_disclaimer = "यह एक original story है जिसे हमारी team ने AI tools (visuals/voice) और creative editing से बनाया है।\n\n"
    final_description = ai_disclaimer + description

    print(f"📤 UPLOADING LONG VIDEO: {title}")

    if not os.path.exists('token.json'):
        print("❌ token.json missing!")
        return

    creds = Credentials.from_authorized_user_file(
        'token.json',
        ['https://www.googleapis.com/auth/youtube.upload']
    )
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)

    request_body = {
        "snippet": {
            "categoryId": CATEGORY_ID,
            "title": title[:100],  # Long videos can have longer titles
            "description": final_description[:5000],
            "tags": tags
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media_file = MediaFileUpload(
        VIDEO_FILE,
        chunksize=-1,
        resumable=True,
        mimetype="video/mp4"
    )
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media_file
    )

    try:
        response = request.execute()
        print(f"✅ VIDEO UPLOADED! https://youtu.be/{response['id']}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

if __name__ == "__main__":
    upload_video()
