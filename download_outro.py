import os
import json
import random
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

def download_random_outro():
    creds_json = os.getenv("GDRIVE_JSON")
    folder_id = os.getenv("GDRIVE_FOLDER_ID")

    if not creds_json or not folder_id:
        print("⚠️ Google Drive Secrets missing! Outro skip kar raha hoon.")
        return

    try:
        # Google Drive se connect karna
        creds_dict = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=creds)

        # Folder ke andar ki saari .mp4 files dhoondhna
        query = f"'{folder_id}' in parents and mimeType='video/mp4' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])

        if not items:
            print("⚠️ Google Drive me koi MP4 file nahi mili!")
            return

        # 100 videos me se 1 Random video chun-na
        random_file = random.choice(items)
        print(f"🎬 Random Outro Selected: {random_file['name']}")

        # Video Download karna
        request = service.files().get_media(fileId=random_file['id'])
        fh = io.FileIO('outro.mp4', 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            
        print("✅ Outro Video Successfully Downloaded as outro.mp4!")
        
    except Exception as e:
        print(f"❌ Google Drive Download Error: {e}")

if __name__ == '__main__':
    download_random_outro()
