import os
import json
import pickle
import logging
import dataclasses
import configparser

import spotipy
import requests.exceptions

from spotipy.oauth2 import SpotifyOAuth

import db

import SpotifyApi

# Setup

config = configparser.ConfigParser()
config.read("config.ini")

## Times

DEFAULT_WAIT_TIME = int(config["SETTINGS"]["DEFAULT_WAIT_TIME"]) # in seconds
ACTIVE_WAIT_TIME = int(config["SETTINGS"]["ACTIVE_WAIT_TIME"])
MAX_ACTIVE_WAIT_TIME = int(config["SETTINGS"]["MAX_ACTIVE_WAIT_TIME"])
PROGRESS_THRESHOLD = float(config["SETTINGS"]["PROGRESS_THRESHOLD"])
ERROR_WAIT_TIME = int(config["SETTINGS"]["ERROR_WAIT_TIME"])



@dataclasses.dataclass(kw_only=True)
class LastUserCheckInfo:
    track: SpotifyApi.CurrentlyPlayingTrack | None
    double_check: bool
    wait_time: int

"""
Represents a user, their connection to the spotify api, and their connection to the database.
"""
class User():


    id : int
    name : str
    wait_time : int
    api : spotipy.Spotify
    spotify_id: str

    last_playing_info: LastUserCheckInfo | None

    def __init__(self, name : str):
        self.name = name
        self.wait_time = 0

        # Get Id or create Id
        results = db.get_user_id(self.name)

        if not results:
            with db.Opener(db.DATABASE) as (con, cur):
                cur.execute("INSERT INTO users (name) VALUES (?)", [self.name])

            self.id = db.get_id("users", self.name)
        else:
            self.id = results

        self.spotify_id = self.get_spotify_id()

        # Setup API connection
        user_cache_path: str = f"./data/.{self.spotify_id}-cache"

        # If cache does not exist, there is a problem
        if not os.path.exists(user_cache_path):
            logging.error(f"No cache not found for user {self.name} at path {user_cache_path}")
            self.api = None
            return

        with open(user_cache_path, 'r') as f:
            cache_data = json.loads(f.read())

        cache_handler = spotipy.MemoryCacheHandler(
            token_info=cache_data)

        self.api = spotipy.Spotify(
        auth_manager = SpotifyOAuth(
            scope=db.SCOPES,
            cache_handler=cache_handler
        ))

        self.load_last_playing()
        if not self.last_playing_info:
            with open('resources/dummy-track-info.json', 'r') as file:
                dummy_track_info = json.loads(file.read())

            self.last_playing_info = LastUserCheckInfo(
                track=SpotifyApi.CurrentlyPlayingTrack.from_json(dummy_track_info),
                double_check=False,
                wait_time=0
            )

    def __str__(self) -> str:
        return self.name

    # The important part, returns wait time
    def do_listening_check(self) -> int:

        wait_time: int = DEFAULT_WAIT_TIME

        try:
            currently_playing_json: dict | None = self.api.current_user_playing_track()
        except requests.exceptions.ConnectionError as e:
            logging.error("Connection error")

            if e.response:
                logging.debug(f"Response: {e.response}")
                if e.response.content:
                    logging.debug(f"Content: {e.response.content}")

            return ERROR_WAIT_TIME
        except Exception as e:
            logging.error(f"Some error happened: {e}")
            return ERROR_WAIT_TIME

        if not currently_playing_json:
            logging.error(f"Currently playing JSON was returned as None from the Spotify API for user {self.name}")
            return ERROR_WAIT_TIME

        currently_playing = SpotifyApi.CurrentlyPlayingTrack.from_json(currently_playing_json)

        self.load_last_playing()

        last_duration: int = self.last_playing_info.track.item.duration_ms
        # TODO @0x01fe last wait time might not work anymore
        last_wait_time: int = self.last_playing_info.wait_time
        last_progress: int = self.last_playing_info.track.progress_ms
        last_track_id: str = self.last_playing_info.track.item.name
        double_check: bool = self.last_playing_info.double_check

        if not currently_playing.is_playing:
            logging.info(f"User \"{self.name}\"is not currently playing a track.")

            if self.last_playing_info:
                self.last_playing_info.double_check = False

            return DEFAULT_WAIT_TIME
        
        # The program gives three seconds of spare because the API call might take some time
        threshold: int = round(currently_playing.item.duration_ms * PROGRESS_THRESHOLD) - 3000

        if double_check and currently_playing.item.id == last_track_id:
            if currently_playing.progress_ms >= threshold:
                logging.info(f"Double Check passed for song {currently_playing.item.name}.")





    # Database Methods


    """
    Get the database id for this user.
    Really only meant as an internal method but no reason to mark it as such.

    Parameters:
        None
    Returns:
        id (str) : id of this user in the database
    """
    def get_spotify_id(self) -> str:
        with db.Opener(db.DATABASE) as (con, cur):
            cur.execute("SELECT * FROM users WHERE id = ?", [self.id, ])

            results = cur.fetchall()

        return results[0][2]

    # Last Playing Methods

    def save_last_playing(self) -> None:

        if not self.last_playing_info:
            logging.error(f"Cannot save last playing for user {self.name} as last playing is type None")
            return

        with open(f'data/{self.spotify_id}_last_playing.pkl', 'wb') as file:
            pickle.dump(self.last_playing_info, file)

    def load_last_playing(self) -> None:

        try:
            with open(f'data/{self.spotify_id}_last_playing.pkl', 'rb') as file:
                self.last_playing_info = pickle.load(file)
        except FileNotFoundError:
            logging.error(f"Cannot load last played data for user {self.name} (File Not Found)")
            self.last_playing_info = None

