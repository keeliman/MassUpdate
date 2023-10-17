import os
import re
import pickle
import datetime
import random
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

DEBUG_MODE = True  # Set this to False for INFO mode

# ---------------- Configuration Loading ----------------

def load_configurations():
    load_dotenv()
    return {
        "API_KEY": os.getenv('API_KEY'),
        "PREFIX": os.getenv('PREFIX'),
        "SUFFIX": os.getenv('SUFFIX'),
        "PLAYLIST_ID": os.getenv('PLAYLIST_ID'),
        "DESCRIPTION": os.getenv('DESCRIPTION').replace('\\n', '\n'),
        "FIRST_INTERVAL": (int(os.getenv('FIRST_INTERVAL_START')), int(os.getenv('FIRST_INTERVAL_END'))),
        "SECOND_INTERVAL": (int(os.getenv('SECOND_INTERVAL_START')), int(os.getenv('SECOND_INTERVAL_END'))),
        "MAX_VIDEOS": int(os.getenv('MAX_VIDEOS', 50)),  # Default to 50 if not set
        "REQ_MAX_RESULT": int(os.getenv('REQ_MAX_RESULT', 50)),  # Default to 50 if not set
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

def get_all_draft_videos(youtube, max_results=400, regex_pattern=r'^\d+$'):
    draft_videos = []
    next_page_token = None

    while True:
        # Perform the request for the current page
        search_response = youtube.search().list(
            part="snippet",
            type="video",
            forMine=True,
            maxResults=max_results,
            pageToken=next_page_token
        ).execute()

        video_items = search_response.get('items', [])

        for video in video_items:
            title = video['snippet']['title']
            match = re.search(regex_pattern, title)
            number = None
            if match:
                number = int(match.group())

            # Check if 'status' is not present in the response (the video is in unscheduled draft)
            if 'status' not in video and number is not None:
                log(f"Video Title: {video['snippet']['title']}, Number: {number}")
                draft_videos.append((number, video))

        # Check if there are more results to fetch
        next_page_token = search_response.get('nextPageToken')
        if not next_page_token:
            break

    # Sort videos based on numbers extracted from the title
    draft_videos.sort(key=lambda x: x[0])

    # Retrieve videos without the number, if needed
    draft_videos = [video for _, video in draft_videos]

    return draft_videos

def get_video_categories(youtube, region_code="US"):
    categories_response = youtube.videoCategories().list(part="snippet", regionCode=region_code).execute()
    return {category["snippet"]["title"]: category["id"] for category in categories_response.get("items", [])}

# Add to playlist
def add_to_playlist(youtube, playlist_id, video_id):
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "position": 0,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id['videoId']
                }
            }
        }
    )
    response = request.execute()
    return response

def update_video(youtube, video, title, description, publish_time, category_id):
    video_id = video['id']['videoId']
    request = youtube.videos().update(
        part="snippet,status",
        body={
            "id": video_id,
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": category_id
            },
            "status": {
                "publishAt": publish_time.isoformat(),
                "privacyStatus": "private",
                "madeForKids": False
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

# ---------------- Scenarios ----------------

def scenario_1():
    youtube = authenticate_with_oauth()
    config = load_configurations()

    # Retrieve video categories
    video_categories = get_video_categories(youtube)

    # Use a default category, e.g., "Entertainment". You can change it as needed.
    default_category_id = video_categories.get("Entertainment", None)

    # Strategy to retrieve videos
    maxResults = config["REQ_MAX_RESULT"]
    draft_videos = get_all_draft_videos(youtube, maxResults)[:config["MAX_VIDEOS"]]
    start_date = config["START_DATE"]
    
    for i, video in enumerate(draft_videos):
        title = process_video_title(video, config["PREFIX"], config["SUFFIX"])
        publish_time = calculate_publish_time(start_date, i, config["FIRST_INTERVAL"], config["SECOND_INTERVAL"])
        try:
            update_video(youtube, video, title, config["DESCRIPTION"], publish_time, default_category_id)
            add_to_playlist(youtube, config["PLAYLIST_ID"], video['id'])
            log(f"Updated video {video['snippet']['title']} for publishing at {publish_time}")
        except HttpError as e:
            log(f"An error occurred while updating video {video['snippet']['title']}: {e}")

# ---------------- Logging ----------------

def log(message):
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")
    else:
        print(f"[INFO] {message}")

# ---------------- Main Execution ----------------

def main():
    scenario_1()

if __name__ == "__main__":
    main()
