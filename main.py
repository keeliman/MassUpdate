import datetime
import random
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# ---------------- Configuration Loading ----------------

def load_configurations():
    load_dotenv()
    return {
        "API_KEY": os.getenv('API_KEY'),
        "PREFIX": os.getenv('PREFIX'),
        "SUFFIX": os.getenv('SUFFIX'),
        "DESCRIPTION": os.getenv('DESCRIPTION').replace('\\n', '\n'),
        "FIRST_INTERVAL": (int(os.getenv('FIRST_INTERVAL_START')), int(os.getenv('FIRST_INTERVAL_END'))),
        "SECOND_INTERVAL": (int(os.getenv('SECOND_INTERVAL_START')), int(os.getenv('SECOND_INTERVAL_END')))
    }

# ---------------- YouTube API Interactions ----------------

def initialize_youtube(api_key):
    return build('youtube', 'v3', developerKey=api_key)

def get_draft_videos(youtube):
    request = youtube.videos().list(part="snippet,status", mine=True, maxResults=50)
    response = request.execute()
    return [item for item in response['items'] if item['status']['privacyStatus'] == 'private']

def update_video(youtube, video, title, description, publish_time):
    video_id = video['id']
    request = youtube.videos().update(
        part="snippet,status",
        body={
            "id": video_id,
            "snippet": {
                "title": title,
                "description": description
            },
            "status": {
                "publishAt": publish_time.isoformat(),
                "privacyStatus": "private"
            }
        }
    )
    response = request.execute()
    return response

# ---------------- Video Processing ----------------

def process_video_title(video, prefix, suffix):
    return prefix + video['snippet']['title'] + suffix

def calculate_publish_time(start_date, index, first_interval, second_interval):
    if index % 2 == 0:
        hour = random.randint(first_interval[0], first_interval[1])
    else:
        hour = random.randint(second_interval[0], second_interval[1])
    return start_date + datetime.timedelta(days=index//2, hours=hour)

# ---------------- Main Execution ----------------

def main():
    config = load_configurations()
    youtube = initialize_youtube(config["API_KEY"])
    
    draft_videos = get_draft_videos(youtube)
    start_date = datetime.datetime.now()
    
    for i, video in enumerate(draft_videos):
        title = process_video_title(video, config["PREFIX"], config["SUFFIX"])
        publish_time = calculate_publish_time(start_date, i, config["FIRST_INTERVAL"], config["SECOND_INTERVAL"])
        try:
            update_video(youtube, video, title, config["DESCRIPTION"], publish_time)
            print(f"Updated video {video['snippet']['title']} for publishing at {publish_time}")
        except HttpError as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()