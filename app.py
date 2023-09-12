#!/usr/local/bin/python3.11
import spotipy
import os
import json
import sqlite3 as sql
from time import sleep
from configparser import ConfigParser
from spotipy.oauth2 import SpotifyOAuth
from requests.exceptions import ConnectionError
from datetime import datetime
from pytz import timezone
import db


config = ConfigParser()
config.read("config.ini")
client_id = config["SPOTIFY"]["CLIENT_ID"]
client_secret = config["SPOTIFY"]["CLIENT_SECRET"]
redirect_uri = config["SPOTIFY"]["REDIRECT_URI"]
scopes = config["SPOTIFY"]["SCOPES"]

wait_time = int(config["SETTINGS"]["WAIT_TIME"]) # in seconds
DATABASE = config["SETTINGS"]["DB_PATH"]
USERS = config["SETTINGS"]["USERS"].split(",")
user_info = {} # Each entry will be a dict like this {'id' : int, 'api' : spotipy.Spotify}

os.environ["SPOTIPY_CLIENT_ID"] = client_id
os.environ["SPOTIPY_CLIENT_SECRET"] = client_secret
os.environ["SPOTIPY_REDIRECT_URI"] = redirect_uri





class Opener():
    def __init__(self):
        self.con = sql.connect(DATABASE)

    def __enter__(self):
        return self.con, self.con.cursor()

    def __exit__(self, type, value, traceback):
        self.con.commit()
        self.con.close()



# Write info from currently_playing to a specified file
def insert_song(currently_playing : dict, user_id : int) -> None:

    # Grab the info from the API response
    song = currently_playing["item"]["name"]
    song_spotify_id = currently_playing["item"]["id"]
    duration = currently_playing["item"]["duration_ms"]

    album = currently_playing["item"]["album"]["name"]
    album_spotify_id = currently_playing["item"]["album"]["id"]
    if not (album_id := db.get_id("albums", album)):
        album_id = db.add_id("albums", album, album_spotify_id)

    new_song_id = db.get_latest_song_id() + 1

    for artist in currently_playing["item"]["artists"]:
        artist_name = artist["name"].replace(" ", "-").lower()
        artist_spotify_id = artist["id"]

        if not (artist_id := db.get_id("artists", artist_name)):
            artist_id = db.add_id("artists", artist_name, artist_spotify_id)

        if not (song_id := db.get_song_id(song, artist_id)):
            db.add_song(new_song_id, song, duration, album_id, artist_id, song_spotify_id)


    # Add to dated
    print("Updating dated table...")
    today = datetime.now(timezone("US/Central"))

    if song_id:
        db.insert(song_id, user_id, today)
    else:
        db.insert(new_song_id, user_id, today)



def main() -> None:

    while True:
        print("#"*20)
        for user in USERS:
            print("-"*20)
            print(f"User: {user} - Looking for a playing song...")

            api = user_info[user]['api']

            try:
                currently_playing = api.current_user_playing_track()
            except ConnectionError:
                print(f"Users : {user} - Connection failed")
                continue

            add = False

            with open("./data/last.json", "r") as f:
                last_track_info = json.loads(f.read())

            if user not in last_track_info:
                add = True
                last_track_info[user] = {}
            else:
                last_progress = last_track_info[user]["last_progress"]
                last_track_title = last_track_info[user]["last_track_title"]

                # Series of checks to see if the program should actually consider this a "listen"
                if currently_playing:
                    if currently_playing["is_playing"]:
                        if last_progress and last_track_title:
                            if (last_progress < currently_playing["progress_ms"]) and (currently_playing["item"]["name"] == last_track_title):
                                add = True
                            elif currently_playing["item"]["name"] != last_track_title:
                                add = True
                        else:
                            add = True

            if add:
                print(f'User: {user} - Song detected, {currently_playing["item"]["name"]}')

                insert_song(currently_playing, user_info[user]['id'])

                last_track_info[user]["last_progress"] = currently_playing["item"]["duration_ms"]
                last_track_info[user]["last_track_title"] = currently_playing["item"]["name"]

                with open("./data/last.json", "w") as f:
                    f.write(json.dumps(last_track_info, indent=4))

            else:
                print(f"User: {user} - Listening check not passed.")


        # Wait before checking again to avoid being rate limited or using my API quota
        print("#"*20 + "\n")
        print(f"Wating {wait_time} seconds...")
        sleep(wait_time)



if __name__ == "__main__":

    # Make sure the database in the config.ini exists.
    if not os.path.exists(DATABASE):
        db.create_db()

    # Make sure users exists
    for user in USERS:
        user_info[user] = {}
        results = db.get_id("users", user)
        if not results:
            with Opener() as (con, cur):
                cur.execute("INSERT INTO users (name) VALUES (?)", [user])
            user_id = db.get_id("users", user)
            user_info[user]['id'] = user_id
        else:
            user_info[user]['id'] = results


    # Get a Spotify Object for each user
    for user in USERS:
        with open(f"./data/.cache-{user_info[user]['id']}", 'r') as f:
            cache_data = json.loads(f.read())

        cache_handler = spotipy.MemoryCacheHandler(token_info=cache_data)
        user_api = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scopes, cache_handler=cache_handler))
        user_info[user]['api'] = user_api

    main()
