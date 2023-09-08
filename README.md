# About

This is a script I wrote to track the amount of time I've listened to various artists, albums, and songs on Spotify. The time listened is stored in an SQLite database.

# Config File Format
This program uses a config.ini file for some basic variables. This is an example of how I have mine set up.


\[SPOTIFY\]
client_id : your_apps_id
client_secret : your_apps_secret
redirect_uri : your_apps_redirect
scopes : user-read-playback-state user-read-currently-playing user-top-read user-read-recently-played user-read-playback-position

\[SETTINGS\]
wait_time : 90
cache_path : ./data/.cache
db_path = ./data/foo.db
user = bar
