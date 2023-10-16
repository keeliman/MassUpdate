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
        "PLAYLIST_ID": os.getenv('PLAYLIST_ID'),
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

    # Récupération des vidéos associées à l'utilisateur authentifié
    search_response = youtube.search().list(part="snippet", type="video", forMine=True, maxResults=50).execute()
    
    video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
    
    if not video_ids:
        return []

    # Récupération des détails des vidéos pour vérifier le statut de confidentialité
    videos_response = youtube.videos().list(part="snippet,status", id=",".join(video_ids), order="title").execute()
    
    # Filtrage des vidéos avec le statut de confidentialité 'private'
    draft_videos = [video for video in videos_response.get('items', []) if video['status']['privacyStatus'] == 'private']
    
    return draft_videos

def get_video_categories(youtube, region_code="US"):
    categories_response = youtube.videoCategories().list(part="snippet", regionCode=region_code).execute()
    return {category["snippet"]["title"]: category["id"] for category in categories_response.get("items", [])}

# add to playlist 
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
    video_id = video['id']
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
                "madeForKids": False  # Set to False to indicate "No, it's not made for kids"
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

# ---------------- Scenarios  ----------------

def scenario_1 () :
    youtube = authenticate_with_oauth()
    config = load_configurations()

    # Récupérer les catégories de vidéos
    video_categories = get_video_categories(youtube)

    # Utilisez une catégorie par défaut, par exemple "Entertainment". Vous pouvez la changer selon vos besoins.
    default_category_id = video_categories.get("Entertainment", None)

    # strategy to retrieve videos 
    draft_videos = get_draft_videos(youtube)[:config["MAX_VIDEOS"]]  # Limit the number of videos
    start_date = config["START_DATE"]
    
    for i, video in enumerate(draft_videos):
        title = process_video_title(video, config["PREFIX"], config["SUFFIX"])
        publish_time = calculate_publish_time(start_date, i, config["FIRST_INTERVAL"], config["SECOND_INTERVAL"])
        try:
            update_video(youtube, video, title, config["DESCRIPTION"], publish_time, default_category_id)
            add_to_playlist(youtube, config["PLAYLIST_ID"], video['id'])
            print(f"Updated video {video['snippet']['title']} for publishing at {publish_time}")
        except HttpError as e:
            print(f"An error occurred while updating video {video['snippet']['title']}: {e}")

# ---------------- Main Execution ----------------
def main():
    scenario_1 ()

if __name__ == "__main__":
    main()
