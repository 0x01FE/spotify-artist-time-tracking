#!/usr/local/bin/python3.11

import os
import sys
import time
import logging
import configparser

import logging.handlers

import db
import UserInfo


# Logging

FORMAT = "%(asctime)s %(levelname)s - %(message)s"
# TODO add env var to pass for debug logs
logging.basicConfig(encoding="utf-8", level=logging.DEBUG, format=FORMAT, handlers=[logging.handlers.RotatingFileHandler(filename="./data/log.log", backupCount=5, maxBytes=1000000), logging.StreamHandler(sys.stdout)])
logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("spotipy").setLevel(logging.ERROR)

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

os.environ["SPOTIPY_CLIENT_ID"] = CLIENT_ID
os.environ["SPOTIPY_CLIENT_SECRET"] = CLIENT_SECRET
os.environ["SPOTIPY_REDIRECT_URI"] = REDIRECT_URI

## Data Dir

if not os.path.exists('./data'):
    logging.info("Data directory does not exist, creating it.")
    os.mkdir('./data')


class SpotifyListener:
    active_users: list[UserInfo.User] = []
    current_user: UserInfo.User

    def __init__(self):

        # Initial User setup
        logging.debug("Getting users for the first time...")
        users: list[UserInfo.User] | None = db.get_users()

        if not users:
            logging.error("No users found.")
            exit(1)

        self.active_users = users
        self.current_user = self.active_users[0]

    # Could return none if there are no users in the dict passed but that should never happen
    def find_lowest_wait_time(self) -> UserInfo.User:
        lowest: UserInfo.User = self.active_users[0]
        for active_user in self.active_users[1:]:
            if active_user.wait_time < lowest.wait_time:
                lowest = active_user

        return lowest

    def check_for_new_users(self) -> None:
        # Check for new users
        logging.debug("Checking for new users...")
        users = db.get_users()

        if not users:
            logging.error("No users found during new user check?")
            exit(1)

        for user in users:

            # Check if user is not in active users
            exists: bool = False
            for active_user in self.active_users:
                if active_user.id == user.id:
                    exists = True
                    break

            # If the user is not in active_users add them
            if not exists:
                self.active_users.append(user)

    # Listen
    def start(self) -> None:
        while True:
            self.check_for_new_users()

            logging.info(f"{self.current_user} - Looking for playing song...")

            self.current_user.do_listening_check()
            self.current_user.save_last_playing()

            # set active user?
            self.current_user = self.find_lowest_wait_time()

            wait_time: int = self.current_user.wait_time

            wait_time = max(wait_time, 5)

            for active_user in self.active_users:
                active_user.wait_time -= wait_time

            logging.info(f"Waiting {wait_time} seconds...")
            time.sleep(wait_time)



def main() -> None:
    spotifyListener = SpotifyListener()

    spotifyListener.start()

if __name__ == "__main__":

    logging.info("Program starting!")

    # Make sure the database in the config.ini exists.
    if not os.path.exists(DATABASE):
        logging.warning(f"No database file found at \"{DATABASE}\", creating new database.")
        db.create_db()

    main()
