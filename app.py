#!/usr/local/bin/python3.11

import os
import sys
import json
import time
import configparser
import datetime
import pytz
import multiprocessing
import logging

import logging.handlers
from requests.exceptions import ConnectionError

import db

# Logging

FORMAT = "%(asctime)s - Thread : %(processName)s %(levelname)s - %(message)s"
logging.basicConfig(encoding="utf-8", level=logging.INFO, format=FORMAT, handlers=[logging.handlers.RotatingFileHandler(filename="./data/log.log", backupCount=5, maxBytes=1000000), logging.StreamHandler(sys.stdout)])


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
users = []

os.environ["SPOTIPY_CLIENT_ID"] = CLIENT_ID
os.environ["SPOTIPY_CLIENT_SECRET"] = CLIENT_SECRET
os.environ["SPOTIPY_REDIRECT_URI"] = REDIRECT_URI


# Check last.json to make sure it has the needed structure.
def check_last_json() -> None:
    if not os.path.exists("./data/last.json"):
        logging.warn("No last.json file found!")
        with open("./data/last.json", "w+") as f:
            pass

    with open("./data/last.json", "r") as f:
        last_track_info = json.loads(f.read())

    for user in users:
        if user.name not in last_track_info:
            logging.warn(f"Invalid JSON data for user {user}!")
            last_track_info[user.name] = {"last_progress" : -1, "last_track_title" : "null_", "double_check" : False}
        else:
            for key in ['last_progress', 'last_track_title', 'double_check', "last_wait_time", "duration"]:
                if key not in last_track_info[user.name]:
                    logging.warn(f"Invalid keys for user {user}!")
                    last_track_info[user.name] = {"last_progress" : -1, "last_track_title" : "null_", "double_check" : False, "last_wait_time" : 0, "duration" : 0}

    with open("./data/last.json", "w") as f:
        f.write(json.dumps(last_track_info, indent=4))

# Write info from currently_playing to a specified file
def insert_song(user : db.User, currently_playing : dict, listen_time : int, skip : bool) -> None:

    # Grab the info from the API response
    song = currently_playing["item"]["name"]
    song_spotify_id = currently_playing["item"]["id"]
    duration = currently_playing["item"]["duration_ms"]

    album = currently_playing["item"]["album"]["name"]
    album_spotify_id = currently_playing["item"]["album"]["id"]
    if not (album_id := user.get_id("albums", album)):
        album_id = user.add_id("albums", album, album_spotify_id)

    new_song_id = user.get_latest_song_id() + 1

    for artist in currently_playing["item"]["artists"]:
        artist_name = artist["name"].replace(" ", "-").lower()
        artist_spotify_id = artist["id"]

        if not (artist_id := user.get_id("artists", artist_name)):
            artist_id = user.add_id("artists", artist_name, artist_spotify_id)

        if not (song_id := user.get_song_id(song, artist_id)):
            user.add_song(new_song_id, song, duration, album_id, artist_id, song_spotify_id)


    # Add to dated
    logging.info(f"Adding entry for song \"{song}\".")
    today = datetime.datetime.now(pytz.timezone("US/Central"))

    if song_id:
        user.insert(song_id, today, listen_time, skip)
    else:
        user.insert(new_song_id, today, listen_time, skip)

def check_user(user : db.User) -> None:
    logging.info("Process started.")
    while True:
        is_playing = False
        wait_time = DEFAULT_WAIT_TIME
        logging.info("Looking for playing song...")

        try:
            currently_playing = user.api.current_user_playing_track()
        except ConnectionError:
            logging.error(f"Connection failed! - {ConnectionError.response.content}")
            time.sleep(ERROR_WAIT_TIME)
            continue

        add = False
        skip = False

        with open("./data/last.json", "r") as f:
            last_track_info = json.loads(f.read())

        last_duration = last_track_info[user.name]["duration"]
        last_wait_time = last_track_info[user.name]["last_wait_time"]
        last_progress = last_track_info[user.name]["last_progress"]
        last_track_title = last_track_info[user.name]["last_track_title"]
        double_check = last_track_info[user.name]["double_check"]

        # Series of checks to see if the program should actually consider this a "listen"
        if currently_playing:
            if currently_playing["is_playing"]:
                is_playing = True
                wait_time = ACTIVE_WAIT_TIME

                current_progress = currently_playing["progress_ms"]
                current_track_title = currently_playing["item"]["name"]
                duration = currently_playing["item"]["duration_ms"]

                logging.info(f"Track found playing \"{current_track_title}\".")

                # The program gives three seconds of spare because the API call might take some time
                threshold = round(duration * PROGRESS_THRESHOLD) - 3000
                if double_check and last_track_title == current_track_title:
                    if current_progress >= threshold:
                        logging.info("Double check passed.")
                        add = True
                        double_check = False
                        listen_time = duration
                    else:
                        logging.info("Double check not passed yet.")
                        wait_time = (round(duration * PROGRESS_THRESHOLD)/1000) - round(current_progress/1000)
                elif double_check and last_track_title != current_track_title:
                    add = True
                    double_check = False
                    skip = True

                    # This part isn't perfect because you could've paused for some amount of time but I just can't tell that with how the spotify API is setup
                    listen_time = last_progress + (last_wait_time - current_progress)

                    # If somehow time is over the duration of the song then just go with the last recorded progress
                    if listen_time > last_duration:
                        listen_time = last_progress

                    # If the time is somehow negative, count it as 0
                    if listen_time < 0:
                        listen_time = 0

                    logging.info(f"Skip detected, recording listen event time as {listen_time}.")

                elif last_track_title != current_track_title and current_progress < threshold:

                    wait_time = (round(duration * PROGRESS_THRESHOLD)/1000) - round(current_progress/1000)

                    if wait_time <= 3:
                        double_check = False
                        add = True
                    else:
                        double_check = True
                        logging.info(f"Playing track \"{current_track_title}\" does not meet time requirment to be recorded.")
                        logging.info(f"Checking again in {wait_time} seconds...")
            else:
                double_check = False

        if add:
            logging.info(f"Song detected, \"{currently_playing['item']['name']}\"")

            insert_song(user, currently_playing, listen_time, skip)

        # Never let the wait time go over the max active wait time
        if wait_time > MAX_ACTIVE_WAIT_TIME and is_playing:
            logging.info("Wait time was over max active wait time. Overriding to max wait time.")
            wait_time = MAX_ACTIVE_WAIT_TIME

        # Write to last.json
        if (double_check and currently_playing) or add or is_playing:
            last_track_info[user.name]["last_progress"] = currently_playing["item"]["duration_ms"]
            last_track_info[user.name]["last_track_title"] = currently_playing["item"]["name"]
            last_track_info[user.name]["double_check"] = double_check
            last_track_info[user.name]["last_wait_time"] = wait_time
            last_track_info[user.name]["duration"] = duration

            with open("./data/last.json", "w") as f:
                f.write(json.dumps(last_track_info, indent=4))

        else:
            logging.info("Listening check not passed.")

        # Wait before checking again to avoid being rate limited or using my API quota
        logging.info(f"Waiting {wait_time} seconds...")
        time.sleep(wait_time)

def main() -> None:
    for user in users:
        logging.info(f"Starting user check process for user {user}...")
        process = multiprocessing.Process(target=check_user, args=(user,), name=f"{user}")
        process.start()

if __name__ == "__main__":

    logging.info("Program starting!")

    # Make sure the database in the config.ini exists.
    if not os.path.exists(DATABASE):
        logging.warn(f"No database file found at \"{DATABASE}\", creating new database.")
        db.create_db()

    users = []
    # Setup all users
    for user in config["SETTINGS"]["USERS"].split(","):
        users.append(db.User(name=user))

    # Check that a valid last.json exists
    check_last_json()


    main()
