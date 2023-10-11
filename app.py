#!/usr/local/bin/python3.11

import os
import json
import time
import configparser
import datetime
import pytz
import multiprocessing

from requests.exceptions import ConnectionError

import db


config = configparser.ConfigParser()
config.read("config.ini")
client_id = config["SPOTIFY"]["CLIENT_ID"]
client_secret = config["SPOTIFY"]["CLIENT_SECRET"]
redirect_uri = config["SPOTIFY"]["REDIRECT_URI"]


default_wait_time = int(config["SETTINGS"]["DEFAULT_WAIT_TIME"]) # in seconds
active_wait_time = int(config["SETTINGS"]["ACTIVE_WAIT_TIME"])
PROGRESS_THRESHOLD = float(config["SETTINGS"]["PROGRESS_THRESHOLD"])
DATABASE = config["SETTINGS"]["DB_PATH"]
users = []

os.environ["SPOTIPY_CLIENT_ID"] = client_id
os.environ["SPOTIPY_CLIENT_SECRET"] = client_secret
os.environ["SPOTIPY_REDIRECT_URI"] = redirect_uri





# Write info from currently_playing to a specified file
def insert_song(user : db.User, currently_playing : dict) -> None:

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
    print(f"User : {user} - Adding entry for song {song}.")
    today = datetime.datetime.now(pytz.timezone("US/Central"))

    if song_id:
        user.insert(song_id, today)
    else:
        user.insert(new_song_id, today)

def check_user(user : db.User) -> None:
    print(f"User : {user} - Process started.")
    while True:
        wait_time = default_wait_time
        print(f"User : {user} - Looking for a playing song...")

        try:
            currently_playing = user.api.current_user_playing_track()
        except ConnectionError:
            print(f"User : {user} - Connection failed!")
            continue

        add = False

        with open("./data/last.json", "r") as f:
            last_track_info = json.loads(f.read())

        if user.name not in last_track_info:
            add = True
            last_track_info[user.name] = {"last_progress" : -1, "last_track_title" : "null_", "double_check" : False}
        else:
            last_progress = last_track_info[user.name]["last_progress"]
            last_track_title = last_track_info[user.name]["last_track_title"]
            double_check = last_track_info[user.name]["double_check"]

            # Series of checks to see if the program should actually consider this a "listen"
            if currently_playing:
                if currently_playing["is_playing"]:

                    wait_time = active_wait_time

                    current_progress = currently_playing["progress_ms"]
                    current_track_title = currently_playing["item"]["name"]
                    duration = currently_playing["item"]["duration_ms"]

                    print(f"User : {user} - Track found playing \"{current_track_title}\".")

                    # The program gives three seconds of spare because the API call might take some time
                    threshold = round(duration * PROGRESS_THRESHOLD) - 3000
                    if double_check and last_track_title == current_track_title and current_progress >= threshold:
                        print(f"User: {user} - Double check passed.")
                        add = True
                        double_check = False

                    elif last_track_title != current_track_title and current_progress < threshold:

                        wait_time = (round(duration * 0.6)/1000) - round(current_progress/1000)

                        if wait_time <= 3:
                            double_check = False
                            add = True
                        else:
                            double_check = True
                            print(f"User : {user} - Playing track \"{current_track_title}\" does not meet time requirment to be recorded.")
                            print(f"User : {user} - Checking again in {wait_time} seconds...")
                else:
                    double_check = False

        if add:
            print(f'User : {user} - Song detected, \"{currently_playing["item"]["name"]}\"')

            insert_song(user, currently_playing)

        if (double_check and currently_playing) or add or currently_playing:
            last_track_info[user.name]["last_progress"] = currently_playing["item"]["duration_ms"]
            last_track_info[user.name]["last_track_title"] = currently_playing["item"]["name"]
            last_track_info[user.name]["double_check"] = double_check

            with open("./data/last.json", "w") as f:
                f.write(json.dumps(last_track_info, indent=4))

        else:
            print(f"User : {user} - Listening check not passed.")


        # Wait before checking again to avoid being rate limited or using my API quota
        print(f"User : {user} - Waiting {wait_time} seconds...")
        time.sleep(wait_time)

def main() -> None:
    for user in users:
        print(f"Starting user check process for user {user}...")
        process = multiprocessing.Process(target=check_user, args=(user,))
        process.start()

if __name__ == "__main__":

    # Make sure the database in the config.ini exists.
    if not os.path.exists(DATABASE):
        db.create_db()

    users = []
    # Setup all users
    for user in config["SETTINGS"]["USERS"].split(","):
        users.append(db.User(name=user))

    main()
