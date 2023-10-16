import os
import pickle
import datetime
import random
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
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
        "SECOND_INTERVAL": (int(os.getenv('SECOND_INTERVAL_START')), int(os.getenv('SECOND_INTERVAL_END'))),
        "MAX_VIDEOS": int(os.getenv('MAX_VIDEOS', 50)),  # Default to 50 if not set
        "START_DATE": datetime.datetime.strptime(os.getenv('START_DATE', datetime.datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d')
    }



# ---------------- OAuth Authentication ----------------

def authenticate_with_oauth():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', ['https://www.googleapis.com/auth/youtube.force-ssl'])
            creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
    
    return build('youtube', 'v3', credentials=creds)

# ---------------- YouTube API Interactions ----------------

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
    youtube = authenticate_with_oauth()
    config = load_configurations()
    
    draft_videos = get_draft_videos(youtube)[:config["MAX_VIDEOS"]]  # Limit the number of videos
    start_date = config["START_DATE"]
    
    for i, video in enumerate(draft_videos):
        title = process_video_title(video, config["PREFIX"], config["SUFFIX"])
        publish_time = calculate_publish_time(start_date, i, config["FIRST_INTERVAL"], config["SECOND_INTERVAL"])
        try:
            update_video(youtube, video, title, config["DESCRIPTION"], publish_time)
            print(f"Updated video {video['snippet']['title']} for publishing at {publish_time}")
        except HttpError as e:
            print(f"An error occurred while updating video {video['snippet']['title']}: {e}")

if __name__ == "__main__":
    main()
