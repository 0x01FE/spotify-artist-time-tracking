import os
import configparser

import spotipy
import spotipy.oauth2

# Setup

config = configparser.ConfigParser()
config.read("config.ini")
CLIENT_ID = config["SPOTIFY"]["CLIENT_ID"]
CLIENT_SECRET = config["SPOTIFY"]["CLIENT_SECRET"]
REDIRECT_URI = config["SPOTIFY"]["REDIRECT_URI"]
SCOPES = config["SPOTIFY"]["SCOPES"]

os.environ["SPOTIPY_CLIENT_ID"] = CLIENT_ID
os.environ["SPOTIPY_CLIENT_SECRET"] = CLIENT_SECRET
os.environ["SPOTIPY_REDIRECT_URI"] = REDIRECT_URI

api = spotipy.Spotify(
    auth_manager=spotipy.oauth2.SpotifyOAuth(scope=SCOPES)
)

api.current_playback()


