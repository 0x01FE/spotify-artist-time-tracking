# About

This is a script I wrote to track the amount of time I've listened to various artists, albums, and songs on Spotify. The time listened is stored in an SQLite database.

# Config File Format
This program uses a config.ini file for some basic variables. This is an example of how I have mine set up.


\[SPOTIFY\]
client_id : your_apps_id\n
client_secret : your_apps_secret\n
redirect_uri : your_apps_redirect\n
scopes : user-read-playback-state user-read-currently-playing user-top-read user-read-recently-played user-read-playback-position

\[SETTINGS\]
wait_time : 90\n
db_path = ./data/foo.db\n
users = bar,xar,tar

# Setup

I personally run this program in a container. If you want to run it another way figure it out.

## Docker


Run this docker command to build the image.

```sh
docker build . -t spotify-tracking:v2
```

After that configure the example docker compose file in the repo and run,
```sh
docker compose up
```
Add the -d flag if you want it to run in the background.



