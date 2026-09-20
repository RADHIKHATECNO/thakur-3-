import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
import base64

def upload():
    video_file = "final_output/merged.mp4"
    if not os.path.exists(video_file):
        print("❌ No video found to upload!")
        return

    # Decode token from base64 secret
    token_b64 = os.getenv("YOUTUBE_TOKEN_BASE64")
    if token_b64:
        with open("token.json", "w") as f:
            f.write(base64.b64decode(token_b64).decode("utf-8"))
    else:
        print("❌ Missing YouTube Token")
        return

    creds = Credentials.from_authorized_user_file("token.json")
    youtube = build("youtube", "v3", credentials=creds)

    request_body = {
        "snippet": {"title": "New AI Story Short", "description": "AI Generated Short"},
        "status": {"privacyStatus": "private"}
    }

    media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
    try:
        request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
        response = request.execute()
        print(f"✅ Upload Success! ID: {response['id']}")
    except Exception as e:
        print(f"❌ Upload Error: {e}")

if __name__ == "__main__":
    upload()
