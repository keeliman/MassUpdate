import datetime
import random
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuration
API_KEY = input("Veuillez entrer votre clé API YouTube : ")
PREFIX = input("Veuillez entrer le préfixe à ajouter aux titres des vidéos : ")
SUFFIX = input("Veuillez entrer le suffixe à ajouter aux titres des vidéos : ")
DESCRIPTION = input("Veuillez entrer la description commune à ajouter aux vidéos : ")

youtube = build('youtube', 'v3', developerKey=API_KEY)

def get_draft_videos():
    request = youtube.videos().list(
        part="snippet,status",
        mine=True,
        maxResults=50
    )
    response = request.execute()
    draft_videos = [item for item in response['items'] if item['status']['privacyStatus'] == 'private']
    return sorted(draft_videos, key=lambda x: int(x['snippet']['title']))

def update_video(video, publish_time):
    video_id = video['id']
    title = PREFIX + video['snippet']['title'] + SUFFIX
    request = youtube.videos().update(
        part="snippet,status",
        body={
            "id": video_id,
            "snippet": {
                "title": title,
                "description": DESCRIPTION
            },
            "status": {
                "publishAt": publish_time.isoformat(),
                "privacyStatus": "private"
            }
        }
    )
    response = request.execute()
    return response

def main():
    start_date = datetime.datetime.now()
    draft_videos = get_draft_videos()
    
    for i, video in enumerate(draft_videos):
        if i % 2 == 0:
            hour = random.randint(1, 9)
        else:
            hour = random.randint(13, 23)
        publish_time = start_date + datetime.timedelta(days=i//2, hours=hour)
        try:
            update_video(video, publish_time)
            print(f"Updated video {video['snippet']['title']} for publishing at {publish_time}")
        except HttpError as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
