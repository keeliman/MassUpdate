To use When you tux outside<br>
___________________________________
EU.MEC.EU wafu-wafu ( @caisse de bruck )<br>
mekua-meke-suku SAV@dir.eu
____________________________________

# YouTube Productivity Mass Update

This script allows users to automate the process of updating YouTube video details and scheduling them for publishing. It's particularly useful for channels that have a large number of draft videos and need to update them in bulk.

## Features

- Authenticate with YouTube API using OAuth2.
- Retrieve all draft videos from a YouTube channel.
- Update video details such as title, description, and schedule them for publishing.
- Add videos to a specific playlist.

## Prerequisites

- Python 3.x
- `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`, `google-api-python-client` and `python-dotenv` libraries. You can install them using pip:

  ```bash
  pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client python-dotenv
- A credentials.json file from the Google Developer Console for OAuth2 authentication.

  
## Configuration

- Rename .env.example to .env.
- Fill in the required details in the .env file.

## Usage
- Run the script: python main.py
- If running for the first time, it will open a browser window for OAuth2 authentication. Log in with the Google account associated with the YouTube channel and grant the necessary permissions.
- The script will then retrieve all draft videos, update their details, and schedule them for publishing.

## Debug Mode
- To enable debug mode, set the DEBUG_MODE variable at the top of the main.py script to True. This will print detailed debug messages during the script's execution.

## Contribution
Feel free to fork this repository, make changes, and submit pull requests. Any kind of contribution is welcome!

## License
This project is open-source and available under the MIT License.
