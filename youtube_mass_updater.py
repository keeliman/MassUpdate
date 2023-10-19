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
    config = {
        "TITLE_PREFIX": os.getenv('TITLE_PREFIX'),
        "TITLE_SUFFIX": os.getenv('TITLE_SUFFIX'),
        "PLAYLIST_ID": os.getenv('PLAYLIST_ID'),
        "DESCRIPTION": os.getenv('DESCRIPTION').replace('\\n', '\n'),
        "FIRST_INTERVAL": (int(os.getenv('FIRST_INTERVAL_START',1)), int(os.getenv('FIRST_INTERVAL_END',9))), # Par défaut ( 1,9 )
        "SECOND_INTERVAL": (int(os.getenv('SECOND_INTERVAL_START',13)), int(os.getenv('SECOND_INTERVAL_END',23))), # Par défaut ( 13 , 23 )
        "TEMP_DATE": os.getenv('TEMP_DATE',datetime.datetime.now().strftime('%Y-%m-%d')), 
        "MAX_VIDEOS": int(os.getenv('MAX_VIDEOS', 400)),  # Par défaut à 400 si non défini
        "REQ_MAX_RESULT": int(os.getenv('REQ_MAX_RESULT', 400)),  # Par défaut à 400 si non défini
        "START_DATE": datetime.datetime.strptime(os.getenv('START_DATE', datetime.datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d'),
        "START_VIDEO_NUMBER": int(os.getenv('START_VIDEO_NUMBER', 130)),  # Par défaut à 130 si non défini
        "END_VIDEO_NUMBER": int(os.getenv('END_VIDEO_NUMBER', 200)),  # Par défaut à 200 si non défini
        "VIDEOS_PER_DAY": int(os.getenv('VIDEOS_PER_DAY', 2)),  # Par défaut à 2 si non défini

    }

    if not validate_configurations(config):
        exit(1)  # Quitter le script si les configurations ne sont pas valides

    return config
    

def validate_configurations(config):
    # Vérification de TITLE_PREFIX
    if not config["TITLE_PREFIX"]:
        logging.error("TITLE_PREFIX est manquant ou vide dans .env.")
        return False

    # Vérification de TITLE_SUFFIX
    if not config["TITLE_SUFFIX"]:
        logging.error("TITLE_SUFFIX est manquant ou vide dans .env.")
        return False

    # Vérification de PLAYLIST_ID
    if not config["PLAYLIST_ID"]:
        logging.error("PLAYLIST_ID est manquant ou vide dans .env.")
        return False

    # Vérification de DESCRIPTION
    if not config["DESCRIPTION"]:
        logging.error("DESCRIPTION est manquant ou vide dans .env.")
        return False


    return True

# ---------------- OAuth Authentication ----------------

def authenticate_with_oauth():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            logging.info("Loaded credentials from token.pickle.")
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("Refreshing expired credentials.")
            creds.refresh(Request())
        else:
            logging.info("No valid credentials found. Starting OAuth2 flow.")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', ['https://www.googleapis.com/auth/youtube.force-ssl'])
            creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            logging.info("Credentials obtained and saved to token.pickle.")
    
    return build('youtube', 'v3', credentials=creds)

# ---------------- YouTube API Interactions ----------------


def get_all_draft_videos(youtube, start_video_number=1, end_video_number=300, max_results=400, regex_pattern=CONTAINS_NUMBERS_REGEX):
    relevant_video_ids = []
    draft_videos = []
    scheduled_videos = []

    next_page_token = None

    # first retrieved suitable IDs
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
            if match:
                number = int(match.group())
                if start_video_number <= number < end_video_number:
                    relevant_video_ids.append(video['id']['videoId'])

        next_page_token = search_response.get('nextPageToken')
        if not next_page_token:
            break

    # Fetch detailed information for relevant videos in batches of 50
    BATCH_SIZE = 50
    for i in range(0, len(relevant_video_ids), BATCH_SIZE):
        batch_ids = relevant_video_ids[i:i+BATCH_SIZE]
        try:
            videos_response = youtube.videos().list(
                part="snippet,status",
                id=",".join(batch_ids)
            ).execute()

            for video in videos_response.get('items', []):
                if video['status']['privacyStatus'] == 'private' and 'publishAt' not in video['status']:
                    draft_videos.append(video)
                    logging.debug(f"Video '{video['snippet']['title']}' is a draft. Adding to draft_videos.")
                elif 'publishAt' in video['status']:
                    scheduled_videos.append(video)
                    logging.debug(f"Video '{video['snippet']['title']}' has a scheduled publish date. Adding to scheduled_videos.")
        except HttpError as e:
            logging.error(f"Error fetching detailed video information for batch starting with {i}: {e}")

    # Sort draft_videos based on numbers extracted from titles
    draft_videos.sort(key=lambda video: int(re.search(regex_pattern, video['snippet']['title']).group()))
    logging.debug("Draft list sorted.")

    # Sort scheduled_videos based on numbers extracted from titles
    scheduled_videos.sort(key=lambda video: int(re.search(regex_pattern, video['snippet']['title']).group()))
    logging.debug("Scheduled Video list sorted.")

    return draft_videos, scheduled_videos


def is_valid_date_format(date_str):
    """Check if the date is in the 'YYYY-MM-DD' format."""
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', date_str))

def get_video_categories(youtube, region_code="US"):
    try:
        logging.debug("Fetching video categories.")
        categories_response = youtube.videoCategories().list(part="snippet", regionCode=region_code).execute()
        logging.debug(f"Received {len(categories_response.get('items', []))} categories.")
        return {category["snippet"]["title"]: category["id"] for category in categories_response.get("items", [])}
        
    except HttpError as e:
        logging.error(f"Error fetching video categories: {e}")
        return {}

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
                    "videoId": video_id
                }
            }
        }
    )
    response = request.execute()
    return response

def update_video(youtube, video, title, description, publish_time, category_id):
    
    # Vérification du titre
    if not title or len(title.strip()) == 0:
        logging.error(f"Attempted to set an empty title for video: {video['snippet']['title']}. Skipping update.")
        return
    elif len(title) > 100:
        logging.error(f"Title length for video {video['snippet']['title']} exceeds the maximum limit. Title: {title}. Skipping update.")
        return

    video_id = video['id']
    try:
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
        
    except HttpError as e:
        logging.error(f"Error updating video {video['snippet']['title']} with title {title}: {e}")
    return response

# ---------------- Video Processing ----------------

def process_video_title(video, TITLE_PREFIX, TITLE_SUFFIX):
    return TITLE_PREFIX + video['snippet']['title'] + TITLE_SUFFIX

def calculate_publish_time(start_date, index, first_interval, second_interval, videos_per_day):
    if videos_per_day == 1:
        hour = random.randint(first_interval[0], second_interval[1])  # Si une seule vidéo par jour, utilisez toute la plage horaire
        return start_date + datetime.timedelta(days=index, hours=hour)
    elif videos_per_day == 2:
        if index % 2 == 0:
            hour = random.randint(first_interval[0], first_interval[1])
        else:
            hour = random.randint(second_interval[0], second_interval[1])
        return start_date + datetime.timedelta(days=index//2, hours=hour)
    else:
        logging.error("Unsupported number of videos per day.")
        return start_date


# ---------------- Scenarios ----------------

def update_videos(youtube, videos, config):
    quota_counter = 0
    MAX_QUOTA = 100000  # Daily quota limit
    start_date = config["START_DATE"]

    video_categories = get_video_categories(youtube)
    quota_counter += 1  # Assume 1 unit for fetching categories

    videos_to_update = []  # List to store videos that need updating

    # First, gather all videos that need updating
    for i, video in enumerate(videos):
        current_title = video['snippet']['title']
        
        # Check if the current title is not numeric
        if not re.match(ONLY_NUMBERS_REGEX, current_title):
            # Reset the title to just the video number
            video_number = int(re.search(CONTAINS_NUMBERS_REGEX, current_title).group())
            video['snippet']['title'] = str(video_number)
            logging.info(f"Resetting title for video '{current_title}' to '{video_number}' due to previous incomplete update.")
        
        # Then process the title with PREFIX and SUFFIX
        title = process_video_title(video, config["TITLE_PREFIX"], config["TITLE_SUFFIX"])
        publish_time = calculate_publish_time(start_date, i, config["FIRST_INTERVAL"], config["SECOND_INTERVAL"], config["VIDEOS_PER_DAY"])
        videos_to_update.append((video, title, publish_time))

    # Update videos while keeping track of the quota
    for video, title, publish_time in videos_to_update:
        if quota_counter + 1650 > MAX_QUOTA:  # Check if the upcoming operations will exceed the quota
            logging.warning("Approaching quota limit. Pausing updates.")
            break

        try:
            update_video(youtube, video, title, config["DESCRIPTION"], publish_time, video_categories["Entertainment"])
            quota_counter += 1600  # 1600 units for video update
            logging.info(f"Updated video: {video['snippet']['title']} with new title: {title} and scheduled publish time: {publish_time}")

            add_to_playlist(youtube, config["PLAYLIST_ID"], video['id'])
            quota_counter += 50  # 50 units for adding to playlist
            logging.info(f"Added video: {video['snippet']['title']} to playlist: {config['PLAYLIST_ID']}")

        except HttpError as e:
            logging.error(f"Error updating video {video['snippet']['title']}: {e}")

        logging.info(f"Quota used so far: {quota_counter}")




def scenario_1():
    youtube = authenticate_with_oauth()
    config = load_configurations()
    
    max_results = config["REQ_MAX_RESULT"]
    draft_videos, scheduled_videos = get_all_draft_videos(youtube, config['START_VIDEO_NUMBER'], config['END_VIDEO_NUMBER'], max_results)
    
    # If scheduled videos are present, determine the earliest scheduled date.
    # Otherwise, use the START_DATE from the configuration.
    if scheduled_videos:
        latest_date = max([datetime.datetime.fromisoformat(video['status']['publishAt']) for video in scheduled_videos])
        latest_date_date_only = latest_date.date()  # This extracts only the date, without the time.
        config["START_DATE"] = datetime.datetime(latest_date_date_only.year, latest_date_date_only.month, latest_date_date_only.day, 0, 0, 0, 0) #set to midnight

        logging.info(f"Found the latest scheduled video date: {config['START_DATE']}. Using this date as the starting point for scheduling draft videos.")
    else:
        logging.info(f"No scheduled videos found. Using default start date from config: {config['START_DATE']}")
    
    update_videos(youtube, draft_videos[:config["MAX_VIDEOS"]], config)
    logging.info("Finished scenario 1.")  


# ---------------- Main Execution ----------------

def main(scenario_name):

    scenarios = {
        "scenario_1": scenario_1
    }

    if scenario_name in scenarios:
        scenarios[scenario_name]()
    else:
        logging.error(f"Scenario '{scenario_name}' not found.")

if __name__ == "__main__":
    # Here, you can specify which scenario to run
    main("scenario_1")