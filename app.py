import spotipy
import os
import json
from time import sleep
from configparser import ConfigParser
from spotipy.oauth2 import SpotifyOAuth



cache_path = "./data/.cache"
json_path = "./data/music-time.json"

wait_time = 90 # in seconds

config = ConfigParser()
config.read("config.ini")
client_id = config["SETTINGS"]["CLIENT_ID"]
client_secret = config["SETTINGS"]["CLIENT_SECRET"]
redirect_uri = config["SETTINGS"]["REDIRECT_URI"]
scopes = config["SETTINGS"]["SCOPES"]

os.environ["SPOTIPY_CLIENT_ID"] = client_id
os.environ["SPOTIPY_CLIENT_SECRET"] = client_secret
os.environ["SPOTIPY_REDIRECT_URI"] = redirect_uri


with open("./data/.cache", "r") as f:
    token_info = json.loads(f.read())


cache_handler = spotipy.MemoryCacheHandler(token_info=token_info)
spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scopes, cache_handler=cache_handler))




# Returns dict of music-time.json
def read() -> dict:
    with open(json_path, "r") as f:
        return json.loads(f.read())



# Writes a dict to music-time.json
def write(info : dict) -> None:
    with open(json_path, "w") as f:
        f.write(json.dumps(info, indent=4))



def main() -> None:
    last_progress = None
    last_track_title = None

    while True:
        print("Looking for a playing song...")
        currently_playing = spotify.current_user_playing_track()
        add = False

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
            data = read()

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

            last_progress = duration
            last_track_title = track_title

            write(data)

        else:
            print("Listening check not passed.")

        # Wait before checking again to avoid being rate limited or using my API quota
        print(f"Wating {wait_time} seconds...")
        sleep(wait_time)




if __name__ == "__main__":
    main()
