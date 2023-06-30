import spotipy
import os
import json
from time import sleep
from configparser import ConfigParser
from spotipy.oauth2 import SpotifyOAuth
from requests.exceptions import ConnectionError
from datetime import datetime




config = ConfigParser()
config.read("config.ini")
client_id = config["SPOTIFY"]["CLIENT_ID"]
client_secret = config["SPOTIFY"]["CLIENT_SECRET"]
redirect_uri = config["SPOTIFY"]["REDIRECT_URI"]
scopes = config["SPOTIFY"]["SCOPES"]

wait_time = int(config["SETTINGS"]["WAIT_TIME"]) # in seconds
cache_path = config["SETTINGS"]["CACHE_PATH"]
json_path = config["SETTINGS"]["JSON_PATH"]

os.environ["SPOTIPY_CLIENT_ID"] = client_id
os.environ["SPOTIPY_CLIENT_SECRET"] = client_secret
os.environ["SPOTIPY_REDIRECT_URI"] = redirect_uri


with open(cache_path, "r") as f:
    token_info = json.loads(f.read())


cache_handler = spotipy.MemoryCacheHandler(token_info=token_info)
spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scopes, cache_handler=cache_handler))




# Writes a dict to music-time.json
def add_time(currently_playing : dict, filename : str) -> None:

    if not os.path.exists(json_path + filename):
        data = { "artists" : {}, "albums" : {}, "songs" : {} }
    else:
        with open(json_path + filename, "r") as f:
            data = json.loads(f.read())

    duration = currently_playing["item"]["duration_ms"]

    # Add to artists listening time
    for artist in currently_playing["item"]["artists"]:
        if artist["name"] not in data["artists"]:
            data["artists"][artist["name"]] = duration

        else:
            data["artists"][artist["name"]] += duration

    # Add to album listen time
    album = currently_playing["item"]["album"]["name"]

    if album not in data["albums"]:
        data["albums"][album] = duration

    else:
        data["albums"][album] += duration


    # Add to song listen time
    track_title = currently_playing["item"]["name"]

    if track_title not in data["songs"]:
        data["songs"][track_title] = duration

    else:
        data["songs"][track_title] += duration

    with open(json_path + filename, "w") as f:
        f.write(json.dumps(data, indent=4))



def main() -> None:

    while True:
        print("#"*20)
        print("Looking for a playing song...")
        try:
            currently_playing = spotify.current_user_playing_track()
        except ConnectionError:
            print(f"ConnectionError, retrying in {wait_time} seconds...")
            sleep(wait_time)
            continue

        add = False

        with open("./data/last.json", "r") as f:
            last_track_info = json.loads(f.read())

        last_progress = last_track_info["last_progress"]
        last_track_title = last_track_info["last_track_title"]

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
            print(f'Song detected, {currently_playing["item"]["name"]}')
            today_file = datetime.now().strftime("%d-%m-%Y") + ".json"

            for file in [today_file, "overall.json"]:
                add_time(currently_playing, file)

            last_track_info["last_progress"] = currently_playing["item"]["duration_ms"]
            last_track_info["last_track_title"] = currently_playing["item"]["name"]

            with open("./data/last.json", "w") as f:
                f.write(json.dumps(last_track_info, indent=4))

        else:
            print("Listening check not passed.")

        # Wait before checking again to avoid being rate limited or using my API quota
        print(f"Wating {wait_time} seconds...")
        print("#"*20 + "\n")
        sleep(wait_time)



if __name__ == "__main__":
    main()
