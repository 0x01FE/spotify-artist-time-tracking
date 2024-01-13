# About

This is a script I wrote to track the amount of time I've listened to various artists, albums, and songs on Spotify. The time listened is stored in an SQLite database.

Current Version: 3.0.0

# Config File Format
This program uses a config.ini file for some basic variables. This is an example of how I have mine set up.

```ini
[SPOTIFY]
client_id = your_apps_id
client_secret = your_apps_secret
redirect_uri = your_apps_redirect
scopes = user-read-playback-state user-read-currently-playing user-top-read user-read-recently-played user-read-playback-position

[SETTINGS]
default_wait_time = 180
active_wait_time = 45
max_active_wait_time = 90
progress_threshold = 0.75
error_wait_time = 30
db_path = ./data/foo.db
```

Here's a brief explantation to some of the more confusing settings.

To understand some of the settings I'll also provide a high level overview of how the program functions.

The program will start and then create a process for each user in the configuration file. After these processes are created they each start a loop that will start by checking with the Spotify API what a user is listening to. If the user is not listening to anything the program will do nothing and wait __default\_wait\_time__ seconds before checking again.

If the user is listening to something but does not meet the __progress\_threshold__ (0.75 being 75% of the way through the song), then it will check the users progress again in x seconds when the user should meet the threshold.

If the program has already added the song the user is listening to it will wait __active\_wait\_time__ seconds before checking again.

__max\_active\_wait\_time__ is the max amount of time in seconds that the program will wait at a time to see if a user is at the threshold to record the track.


# Setup

I personally run this program in a container. If you want to run it another way figure it out.

## Docker


Run this docker command to build the image.

```sh
docker build . -t spotify-tracking:v3
```

After that configure the example docker compose file in the repo and run,
```sh
docker compose up
```
Add the -d flag if you want it to run in the background.



