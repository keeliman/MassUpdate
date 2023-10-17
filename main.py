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
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

ONLY_NUMBERS_REGEX = r'^\d+$'
CONTAINS_NUMBERS_REGEX = r'\d+'

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
        "TEMP_DATE": os.getenv('TEMP_DATE'),
        "MAX_VIDEOS": int(os.getenv('MAX_VIDEOS', 50)),  # Par défaut à 50 si non défini
        "REQ_MAX_RESULT": int(os.getenv('REQ_MAX_RESULT', 50)),  # Par défaut à 50 si non défini
        "START_DATE": datetime.datetime.strptime(os.getenv('START_DATE', datetime.datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d'),
        "START_VIDEO_NUMBER": int(os.getenv('START_VIDEO_NUMBER', 130)),  # Par défaut à 130 si non défini
        "END_VIDEO_NUMBER": int(os.getenv('END_VIDEO_NUMBER', 200))  # Par défaut à 200 si non défini
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


def get_all_draft_videos(youtube, start_video_number=1, end_video_number=300, max_results=400, regex_pattern=CONTAINS_NUMBERS_REGEX):
    draft_videos = []
    next_page_token = None

    while True:
        try:
            search_response = youtube.search().list(
                part="snippet",
                type="video",
                forMine=True,
                maxResults=max_results,
                pageToken=next_page_token
            ).execute()
        except HttpError as e:
            logging.error(f"Error fetching videos: {e}")
            break

        video_items = search_response.get('items', [])

        for video in video_items:
            title = video['snippet']['title']
            match = re.search(regex_pattern, title)
            number = None
            if match:
                number = int(match.group())
                if start_video_number <= number < end_video_number:
                    if 'status' not in video:
                        draft_videos.append(video)
                        logging.debug(f"Adding video: {title}, Number: {number}")

        next_page_token = search_response.get('nextPageToken')
        if not next_page_token:
            break

    # Sort videos based on numbers extracted from the title
    draft_videos.sort(key=lambda x: int(re.search(regex_pattern, x['snippet']['title']).group()))

    return draft_videos

def get_scheduled_videos_on_date(youtube, target_date, max_results=400, regex_pattern=ONLY_NUMBERS_REGEX):
    scheduled_videos = []
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

        video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
        
        # Fetch video details using video IDs
        videos_response = youtube.videos().list(
            part="snippet,status",
            id=",".join(video_ids)
        ).execute()

        for video in videos_response.get('items', []):
            title = video['snippet']['title']
            match = re.search(regex_pattern, title)
            number = None
            if match:
                number = int(match.group())

            # Check if the video is private and scheduled for the target date
            if video['status']['privacyStatus'] == 'private' and video['status'].get('publishAt', '').startswith(target_date):
                logging.debug(f"Video Title: {video['snippet']['title']}, Scheduled Date: {video['status']['publishAt']}")
                scheduled_videos.append((number, video))

        # Check if there are more results to fetch
        next_page_token = search_response.get('nextPageToken')
        if not next_page_token:
            break

    # Sort videos based on numbers extracted from the title
    scheduled_videos.sort(key=lambda x: x[0])

    # Retrieve videos without the number, if needed
    scheduled_videos = [video for _, video in scheduled_videos]

    return scheduled_videos

def is_valid_date_format(date_str):
    """Check if the date is in the 'YYYY-MM-DD' format."""
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', date_str))

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

def update_videos(youtube, config, draft_videos):
    video_categories = get_video_categories(youtube)
    default_category_id = video_categories.get("Entertainment", None)
    start_date = config["START_DATE"]

    for i, video in enumerate(draft_videos):
        title = process_video_title(video, config["PREFIX"], config["SUFFIX"])
        publish_time = calculate_publish_time(start_date, i, config["FIRST_INTERVAL"], config["SECOND_INTERVAL"])

        try:
            update_video(youtube, video, title, config["DESCRIPTION"], publish_time, default_category_id)
            add_to_playlist(youtube, config["PLAYLIST_ID"], video['id'])
            logging.debug(f"Updated video {video['snippet']['title']} for publishing at {publish_time}")
        except HttpError as e:
            logging.debug(f"An error occurred while updating video {video['snippet']['title']}: {e}")


def scenario_1():
    youtube = authenticate_with_oauth()
    config = load_configurations()
    max_results = config["REQ_MAX_RESULT"]
    draft_videos = get_all_draft_videos(youtube, config['START_VIDEO_NUMBER'], config['END_VIDEO_NUMBER'], max_results)[:config["MAX_VIDEOS"]]

    update_videos(youtube, config, draft_videos)


def scenario_2():
    youtube = authenticate_with_oauth()
    config = load_configurations()
    temp_date = config['TEMP_DATE']

    if not is_valid_date_format(temp_date):
        logging.error("Error: TEMP_DATE is not in the 'YYYY-MM-DD' format. Please correct the format in .env.")
        exit(1)

    max_results = config["REQ_MAX_RESULT"]
    draft_videos = get_scheduled_videos_on_date(youtube, temp_date, max_results)[:config["MAX_VIDEOS"]]

    update_videos(youtube, config, draft_videos)


# ---------------- Main Execution ----------------

def main():
    scenario_1()

if __name__ == "__main__":
    main()
