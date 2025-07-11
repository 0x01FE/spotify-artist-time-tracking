import os
import json
import pytz
import math
import pickle
import logging
import datetime
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


# This object gets cached and read a lot
@dataclasses.dataclass(kw_only=True)
class LastUserCheckInfo:
    track: SpotifyApi.CurrentlyPlayingTrack
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

    last_playing_info: LastUserCheckInfo

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
            logging.error(f"No cache found for user {self.name} at path {user_cache_path}")
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
    def do_listening_check(self) -> None:

        self.wait_time: int = DEFAULT_WAIT_TIME

        try:
            currently_playing_json: dict | None = self.api.current_user_playing_track()
        except requests.exceptions.ConnectionError as e:
            logging.error("Connection error")

            if e.response:
                logging.debug(f"Response: {e.response}")
                if e.response.content:
                    logging.debug(f"Content: {e.response.content}")

            self.wait_time = ERROR_WAIT_TIME
            return
        except Exception as e:
            logging.error(f"Some error happened: {e}")
            self.wait_time = ERROR_WAIT_TIME
            return

        if not currently_playing_json:
            logging.error(f"Currently playing JSON was returned as None from the Spotify API for user {self.name}")
            self.last_playing_info.double_check = False
            self.wait_time = ERROR_WAIT_TIME
            return

        currently_playing = SpotifyApi.CurrentlyPlayingTrack.from_json(currently_playing_json)

        self.load_last_playing()

        double_check: bool = self.last_playing_info.double_check

        if not currently_playing.is_playing:
            logging.info(f"User \"{self.name}\"is not currently playing a track.")

            if self.last_playing_info:
                self.last_playing_info.double_check = False

            self.wait_time = DEFAULT_WAIT_TIME
            return

        # The program gives three seconds of spare because the API call might take some time
        threshold: int = round(currently_playing.item.duration_ms * PROGRESS_THRESHOLD) - 3000
        current_progress = currently_playing.progress_ms
        duration = currently_playing.item.duration_ms

        if double_check and currently_playing.item.id == self.last_playing_info.track.item.id:
            if currently_playing.progress_ms >= threshold:
                logging.info(f"Double Check passed for song {currently_playing.item.name}.")
                self.last_playing_info.double_check = False

                self.insert_song(
                    currently_playing,
                    duration,
                    False
                )

                self.last_playing_info.track = currently_playing
                self.last_playing_info.wait_time = ACTIVE_WAIT_TIME

            else:
                logging.info(f"Double check not passed yet for song {currently_playing.item.name}.")
                self.wait_time = math.ceil((round(duration * PROGRESS_THRESHOLD)/1000) - round(current_progress/1000))

                self.wait_time = min(self.wait_time, MAX_ACTIVE_WAIT_TIME)

                logging.info(f"Checking again in {self.wait_time} seconds...")

                return

        elif double_check and self.last_playing_info.track.item.id != currently_playing.item.id:
            self.last_playing_info.double_check = False

            listen_time: int = self.last_playing_info.track.progress_ms + ((self.last_playing_info.wait_time * 1000) - currently_playing.progress_ms)

            if listen_time < 0:
                logging.error(f'Time was negative\n{self.last_playing_info.track.progress_ms=}\n{self.wait_time*1000=}\n{currently_playing.progress_ms}')
            else:
                self.insert_song(
                    self.last_playing_info.track,
                    listen_time,
                    True
                )

            if current_progress < threshold:
                proposed_wait_time = round((duration * PROGRESS_THRESHOLD)/1000) - round(current_progress/1000)

                if proposed_wait_time <= 10:
                    self.last_playing_info.double_check = False

                    self.insert_song(
                        currently_playing,
                        duration,
                        False
                    )

                else:
                    self.last_playing_info.double_check = True
                    self.wait_time = min(proposed_wait_time, MAX_ACTIVE_WAIT_TIME)
                    self.last_playing_info.track = currently_playing
                    return
            else:
                self.last_playing_info.double_check = False

                self.insert_song(
                    currently_playing,
                    duration,
                    False
                )

            # wont add again because of double check btw?

            self.last_playing_info.track = currently_playing
            self.last_playing_info.wait_time = ACTIVE_WAIT_TIME

        elif self.last_playing_info.track.item.id != currently_playing.item.id and current_progress < threshold:
            proposed_wait_time = round((duration * PROGRESS_THRESHOLD)/1000) - round(current_progress/1000)

            if proposed_wait_time <= 10:
                self.last_playing_info.double_check = False

                self.insert_song(
                    currently_playing,
                    duration,
                    False
                )

            else:
                self.last_playing_info.double_check = True
                self.wait_time = min(proposed_wait_time, MAX_ACTIVE_WAIT_TIME)
                self.last_playing_info.track = currently_playing
                return


        self.wait_time = ACTIVE_WAIT_TIME



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
    
    def insert_song(self, spotify_currently_playing : SpotifyApi.CurrentlyPlayingTrack, listen_time : int, skip : bool) -> None:

        # Grab the info from the API response
        song = spotify_currently_playing.item.name
        song_spotify_id = spotify_currently_playing.item.id
        duration = spotify_currently_playing.item.duration_ms

        album = spotify_currently_playing.item.album.name
        album_spotify_id = spotify_currently_playing.item.album.id
        if not (album_id := db.get_album_id(album)):
            cover_art_url: str = spotify_currently_playing.item.album.images[0].url
            album_id = db.add_album(album, album_spotify_id, cover_art_url)

        new_song_id = db.get_latest_song_id() + 1

        logging.debug(f"Adding song {song} for user {self.name} with time {listen_time} ms. Skip: {skip}")

        for artist in spotify_currently_playing.item.artists:
            artist_name = artist.name.replace(" ", "-").lower()
            artist_spotify_id = artist.id

            if not (artist_id := db.get_artist_id(artist_name)):
                artist_json: dict | None = self.api.artist(artist_spotify_id)

                if not artist_json:
                    logging.error(f'Artist {artist.name} could not be grabbed from the Spotify API.')
                    icon_url = None
                else:
                    artist_info = SpotifyApi.Artist.from_json(artist_json)

                    if not artist_info.images:
                        logging.error(f'No images found for artist {artist.name}.')
                        icon_url = None
                    else:
                        icon_url: str | None = artist_info.images[0].url

                artist_id: int = db.add_artist(artist_name, artist_spotify_id, icon_url)

            if not (song_id := db.get_song_id(song, artist_id)):
                db.add_song(new_song_id, song, duration, album_id, artist_id, song_spotify_id)


        # Add to dated
        logging.info(f"Adding entry for song \"{song}\".")
        today = datetime.datetime.now(pytz.timezone("US/Central"))

        if song_id:
            db.insert(song_id, self, today, listen_time, skip)
        else:
            db.insert(new_song_id, self, today, listen_time, skip)

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

