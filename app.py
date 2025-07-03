#!/usr/local/bin/python3.11

import os
import sys
import math
import json
import time
import pytz
import logging
import datetime
import configparser


import logging.handlers
import requests.exceptions

import db
import UserInfo

import SpotifyApi

# Logging

FORMAT = "%(asctime)s %(levelname)s - %(message)s"
# TODO add env var to pass for debug logs
logging.basicConfig(encoding="utf-8", level=logging.DEBUG, format=FORMAT, handlers=[logging.handlers.RotatingFileHandler(filename="./data/log.log", backupCount=5, maxBytes=1000000), logging.StreamHandler(sys.stdout)])


# Setup

config = configparser.ConfigParser()
config.read("config.ini")
CLIENT_ID = config["SPOTIFY"]["CLIENT_ID"]
CLIENT_SECRET = config["SPOTIFY"]["CLIENT_SECRET"]
REDIRECT_URI = config["SPOTIFY"]["REDIRECT_URI"]

## Times

DEFAULT_WAIT_TIME = int(config["SETTINGS"]["DEFAULT_WAIT_TIME"]) # in seconds
ACTIVE_WAIT_TIME = int(config["SETTINGS"]["ACTIVE_WAIT_TIME"])
MAX_ACTIVE_WAIT_TIME = int(config["SETTINGS"]["MAX_ACTIVE_WAIT_TIME"])
PROGRESS_THRESHOLD = float(config["SETTINGS"]["PROGRESS_THRESHOLD"])
ERROR_WAIT_TIME = int(config["SETTINGS"]["ERROR_WAIT_TIME"])

DATABASE = config["SETTINGS"]["DB_PATH"]
active_users: list[UserInfo.User] = []

os.environ["SPOTIPY_CLIENT_ID"] = CLIENT_ID
os.environ["SPOTIPY_CLIENT_SECRET"] = CLIENT_SECRET
os.environ["SPOTIPY_REDIRECT_URI"] = REDIRECT_URI

## Data Dir

if not os.path.exists('./data'):
    logging.info("Data directory does not exist, creating it.")
    os.mkdir('./data')


# Check last.json to make sure it has the needed structure.
def check_last_json() -> None:
    users: list[UserInfo.User] = db.get_users()

    if not os.path.exists("./data/last.json"):
        logging.warning("No last.json file found!")
        with open("./data/last.json", "w+") as f:
            pass

    with open("./data/last.json", "r") as f:
        last_track_info = json.loads(f.read())

    # TODO @0x01fe key this by user id instead of name
    for user in users:
        if user.name not in last_track_info:
            logging.warning(f"Invalid JSON data for user {user}!")
            last_track_info[user.name] = {"last_progress" : -1, "last_track_title" : "null_", "double_check" : False}
        else:
            for key in ['last_progress', 'last_track_title', 'double_check', "last_wait_time", "duration"]:
                if key not in last_track_info[user.name]:
                    logging.warning(f"Invalid keys for user {user}!")
                    last_track_info[user.name] = {"last_progress" : -1, "last_track_title" : "null_", "double_check" : False, "last_wait_time" : 0, "duration" : 0}

    with open("./data/last.json", "w") as f:
        f.write(json.dumps(last_track_info, indent=4))

# Write info from currently_playing to a specified file
def insert_song(user : UserInfo.User, currently_playing : SpotifyApi.CurrentlyPlayingTrack, listen_time : int, skip : bool) -> None:

    # Grab the info from the API response
    song = currently_playing.item.name
    song_spotify_id = currently_playing.item.id
    duration = currently_playing.item.duration_ms

    album = currently_playing.item.album.name
    album_spotify_id = currently_playing.item.album.id
    if not (album_id := db.get_album_id(album)):
        cover_art_url: str = currently_playing.item.album.images[0].url
        album_id = db.add_album(album, album_spotify_id, cover_art_url)

    new_song_id = db.get_latest_song_id() + 1

    logging.debug(f"Adding song {song} for user {user} with time {listen_time} ms. Skip: {skip}")

    for artist in currently_playing.item.artists:
        artist_name = artist.name.replace(" ", "-").lower()
        artist_spotify_id = artist.id

        if not (artist_id := db.get_artist_id(artist_name)):
            artist_json: dict | None = user.api.artist(artist_spotify_id)

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
        db.insert(song_id, user, today, listen_time, skip)
    else:
        db.insert(new_song_id, user, today, listen_time, skip)

# Could return none if there are no users in the dict passed but that should never happen
def find_lowest_wait_time(active_users : list[UserInfo.User]) -> UserInfo.User:
    lowest: UserInfo.User = active_users[0]
    for active_user in active_users[1:]:
        if active_user.wait_time < lowest.wait_time:
            lowest = active_user

    return lowest

def check_for_new_users(current_users: list[UserInfo.User]) -> list[UserInfo.User]:
    # Check for new users
    logging.debug("Checking for new users...")
    users = db.get_users()

    if not users:
        logging.error("No users found during new user check?")
        exit(1)

    for user in users:

        # Check if user is not in active users
        exists: bool = False
        for active_user in current_users:
            if active_user.id == user.id:
                exists = True
                break

        # If the user is not in active_users add them
        if not exists:
            current_users.append(user)

    return current_users

def main() -> None:

    # Initial User setup
    logging.debug("Getting users for the first time...")
    users: list[UserInfo.User] | None = db.get_users()

    if not users:
        logging.error("No users found.")
        exit(1)

    for user in users:
        active_users.append(user)

    logging.info("Listen check loop started.")

    current_user: UserInfo.User = users[0] # Current user the loop is checking on

    # The guts of the program
    while True:

        active_users = check_for_new_users(active_users)

        # Do the listen check on current user
        logging.info(f"{current_user} - Looking for playing song...")

        is_playing: bool = False
        wait_time: int = DEFAULT_WAIT_TIME

        try:
            currently_playing_json: dict | None = current_user.api.current_user_playing_track()
        except requests.exceptions.ConnectionError as e:
            logging.error("Connection error")

            if e.response:
                logging.debug(f"Response: {e.response}")
                if e.response.content:
                    logging.debug(f"Content: {e.response.content}")

            time.sleep(ERROR_WAIT_TIME)
            continue
        except Exception as e:
            logging.error(f"Some error happened: {e}")
            time.sleep(ERROR_WAIT_TIME)
            continue

        if currently_playing_json:

            currently_playing = SpotifyApi.CurrentlyPlayingTrack.from_json(currently_playing_json)

            add: bool = False
            skip: bool = False

            current_user.load_last_playing()

            if current_user.last_playing_info:
                last_duration: int = current_user.last_playing_info.track.item.duration_ms
                # TODO @0x01fe last wait time might not work anymore
                last_wait_time: int = current_user.last_playing_info.wait_time
                last_progress: int = current_user.last_playing_info.track.progress_ms
                last_track_title: str = current_user.last_playing_info.track.item.name
                double_check: bool = current_user.last_playing_info.double_check
            else:
                last_duration: int = 0
                last_wait_time: int = 0
                last_progress: int = 0
                last_track_title: str = ""
                double_check: bool = False

            # Series of checks to see if the program should actually consider this a "listen"
            if currently_playing.is_playing:
                is_playing = True
                wait_time = ACTIVE_WAIT_TIME

                current_progress = currently_playing.progress_ms
                current_track_title = currently_playing.item.name
                duration = currently_playing.item.duration_ms

                logging.info(f"Track found playing \"{current_track_title}\" for user {current_user.name}.")

                # The program gives three seconds of spare because the API call might take some time
                threshold: int = round(duration * PROGRESS_THRESHOLD) - 3000
                # TODO @0x01fe check by track id instead of title
                if double_check and last_track_title == current_track_title:
                    if current_progress >= threshold:
                        logging.info("Double check passed.")
                        add = True
                        double_check = False
                        listen_time = duration
                    else:
                        logging.info("Double check not passed yet.")
                        wait_time = math.ceil((round(duration * PROGRESS_THRESHOLD)/1000) - round(current_progress/1000))
                        logging.info(f"Checking again in {wait_time} seconds...")
                elif double_check and last_track_title != current_track_title:
                    add = True
                    double_check = False
                    skip = True

                    # This part isn't perfect because you could've paused for some amount of time but I just can't tell that with how the spotify API is setup
                    listen_time = current_user.last_playing_info.track.progress_ms + ((current_user.last_playing_info.wait_time * 1000) - currently_playing.progress_ms)

                    # If the time is somehow negative, don't add it
                    if listen_time < 0:
                        logging.debug(f'Time was negative\n{current_user.last_playing_info.track.progress_ms=}\n{wait_time*1000=}\n{currently_playing.progress_ms}')
                        add = False

                    logging.info(f"Skip detected, recording listen event time as {listen_time}.")

                    # Now check the currently playing song
                    # wont add again because of double check btw?

                elif last_track_title != current_track_title and current_progress < threshold:

                    wait_time = int(round(duration * PROGRESS_THRESHOLD)/1000) - round(current_progress/1000)

                    if wait_time <= 10:
                        double_check = False
                        listen_time = duration
                        add = True
                    else:
                        double_check = True
                        logging.info(f"Playing track \"{current_track_title}\" does not meet time requirment to be recorded.")
                        logging.info(f"Checking again in {wait_time} seconds...")
            else:
                double_check = False

        else:
            logging.error(f"Currently playing JSON was returned as None from the Spotify API for user {user.name}")
            double_check = False

        if add:
            to_record = currently_playing
            if skip and current_user.last_playing_info:
                logging.info("Skip detected, actually recording _last_ played track.")
                to_record = current_user.last_playing_info.track

            if to_record:

                logging.info(f"Song detected, \"{to_record.item.name}\"")

                insert_song(current_user, to_record, listen_time, skip)
            else:
                logging.error("Somehow the to_record track was None?")

        # Never let the wait time go over the max active wait time
        if wait_time > MAX_ACTIVE_WAIT_TIME and is_playing:
            logging.info("Wait time was over max active wait time. Overriding to max wait time.")
            wait_time = MAX_ACTIVE_WAIT_TIME

        # Write last track info
        if (double_check and currently_playing) or add or is_playing:

            current_user.last_playing_info = UserInfo.LastUserCheckInfo(
                track=currently_playing,
                double_check=double_check,
                wait_time=wait_time
            )

            current_user.save_last_playing()

        else:
            logging.info("Listening check not passed.")


        # Figure out the next user to check and the wait time.
        current_user.wait_time = wait_time

        current_user = find_lowest_wait_time(active_users)
        wait_time = current_user.wait_time

        # wait 5 seconds to avoid rate limits if 0 or under
        if wait_time <= 0:
            wait_time = 5

        # Change all other wait times to account for the passage of time
        for active_user in active_users:
            active_user.wait_time -= wait_time

        logging.info(f"Waiting {wait_time} seconds...")
        time.sleep(wait_time)

if __name__ == "__main__":

    logging.info("Program starting!")

    # Make sure the database in the config.ini exists.
    if not os.path.exists(DATABASE):
        logging.warning(f"No database file found at \"{DATABASE}\", creating new database.")
        db.create_db()

    # Check that a valid last.json exists
    check_last_json()

    main()
