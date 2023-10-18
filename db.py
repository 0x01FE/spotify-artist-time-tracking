#!/usr/local/bin/python3.11

from typing import Literal
import json
import sqlite3
import datetime
import logging
import configparser

import spotipy

from spotipy.oauth2 import SpotifyOAuth

'''
Note to anyone reading this. I'm aware the way I'm selecting the tables is bad!
I'll rewrite it using SQLAlchemy I swear
'''


# Get logger

logger = logging.getLogger(__name__)

# Note that SQLite can only work with dates in the YYYY-MM-DD format.

config = configparser.ConfigParser()
config.read("config.ini")
SCOPES = config["SPOTIFY"]["SCOPES"]
DATABASE = config["SETTINGS"]["DB_PATH"]


class Opener():
    def __init__(self, database):
        self.con = sqlite3.connect(database)

    def __enter__(self):
        return self.con, self.con.cursor()

    def __exit__(self, type, value, traceback):
        self.con.commit()
        self.con.close()


"""
Represents a user, their connection to the spotify api, and their connection to the database.
"""
class User():


    id : int
    name : str
    api : spotipy.Spotify


    def __init__(self, name : str):
        self.name = name

        # Get Id or create Id
        results = self.get_id("users", self.name)

        if not results:
            with Opener(DATABASE) as (con, cur):
                cur.execute("INSERT INTO users (name) VALUES (?)", [self.name])

            self.id = self.get_id("users", self.name)
        else:
            self.id = results

        # Setup API connection
        with open(f"./data/.cache-{self.id}", 'r') as f:
            cache_data = json.loads(f.read())

        cache_handler = spotipy.MemoryCacheHandler(
            token_info=cache_data)

        self.api = spotipy.Spotify(
            auth_manager = SpotifyOAuth(
                scope=SCOPES,
                cache_handler=cache_handler
            ))

    def __str__(self) -> str:
        return self.name


    # Database Methods


    """
    Get the latest song id.

    Why:
        Some songs need to have the same id to support my system for handling a song with multiple artists.

    Parameters:
        None

    Returns:
        id (int) : latest id added
    """
    def get_latest_song_id(self) -> int:
        with Opener(DATABASE) as (con, cur):
            cur.execute("SELECT * FROM songs ORDER BY id DESC LIMIT 1")

            results = cur.fetchall()

        if not results:
            return 0
        else:
            return results[0][0]


    """
    Add an artist, album, or user to the database.

    Parameters:
        table (Literal[str]) : Table that you are adding name to
        name (str) : Name of the item you are adding
        spotify_id (str | None) : spotify_id if this is hooked to spotify

    Returns:
        id (int) : Id of the added item
    """
    def add_id(self, table : Literal["artists", "albums", "users"], name : str, spotify_id : str | None = None) -> int:
        with Opener(DATABASE) as (con, cur):
            if spotify_id:
                cur.execute("INSERT INTO '{}' (name, spotify_id) VALUES (?, ?)".format(table), [name, spotify_id])
            else:
                cur.execute("INSERT INTO '{}' (name) VALUES (?)".format(table), [name])

        return cur.lastrowid


    """
    Adds a song to the database.

    Parameters:
        id (int) : Id of the song you're adding (use the value from get_latest_song_id + 1)
        name (str) : Name of the song you're adding
        album (int) : Album id
        artist (int) : Artist id
        spotify_id (str) : Spotify song id

    Returns:
        id (int) : id of the song added
    """
    def add_song(self, id : int, name : str, length : int, album : int, artist : int, spotify_id : str | None = None) -> int:
        with Opener(DATABASE) as (con, cur):
            if spotify_id:
                cur.execute("INSERT INTO songs (id, name, length, album, artist, spotify_id) VALUES (?, ?, ?, ?, ?, ?)", [id, name, length, album, artist, spotify_id])
            else:
                cur.execute("INSERT INTO songs (id, name, length, album, artist) VALUES (?, ?, ?, ?, ?)", [id, name, length, album, artist])

        return cur.lastrowid


    """
    Get the id of some artist, album, or user.

    Parameters:
        table (str) : Name of the table the item is in
        name (str) : Name of the item you're looking for

    Returns:
        id (int | None) : Id if found, otherwise None.
    """
    def get_id(self, table : Literal["artists", "albums", "users"], name : str) -> int | None:
        with Opener(DATABASE) as (con, cur):
            cur.execute("SELECT * FROM '{}' WHERE name = ?".format(table), [name])
            results = cur.fetchall()

        if results:
            return results[0][0]
        return None


    """
    Get the id of a song by name and artist id.

    Paramters:
        song_name (str) : Name of the song
        artist_id (int) : Id of the artist

    returns:
        id (int | None) : Id if found, otherwise None.
    """
    def get_song_id(self, song_name : str, artist_id : int) -> int | None:
        with Opener(DATABASE) as (con, cur):
            cur.execute("SELECT * FROM songs WHERE name = ? AND artist = ?", [song_name, artist_id])
            results = cur.fetchall()

        if results:
            return results[0][0]
        return None


    """
    Insert an event of a user listening to a song.

    Parameters:
        song (int) : Id of the song in the event.
        date (datetime.datetime) : Datetime object representing the day of the event.

    Returns:
        None
    """
    def insert(
        self,
        song : int,
        date : datetime.datetime
    ) -> None:
        with Opener(DATABASE) as (con, cur):
            date = date.strftime("%Y-%m-%d")

            cur.execute("INSERT INTO dated VALUES (?, ?, ?)", [song, self.id, date])


"""
Creates the database and setups the Schema.

Parameters:
    None

Returns:
    None
"""
def create_db() -> None:
    # Create the file
    with open(DATABASE, 'w') as f:
        pass

    with Opener(DATABASE) as (con, cur):
        cur.execute('CREATE TABLE "albums" ( "id" INTEGER, "name" TEXT NOT NULL, "spotify_id" TEXT, PRIMARY KEY("id" AUTOINCREMENT) )')
        cur.execute('CREATE TABLE "artists" ( "id" INTEGER, "name" TEXT NOT NULL, "spotify_id" TEXT, PRIMARY KEY("id" AUTOINCREMENT) )')
        cur.execute('CREATE TABLE "dated" ( "song" INTEGER NOT NULL, "user" INTEGER NOT NULL, "date" TEXT NOT NULL )')
        cur.execute('CREATE TABLE "songs" ( "id" INTEGER NOT NULL, "name" TEXT NOT NULL, "length" INTEGER NOT NULL, "album" INTEGER NOT NULL, "artist" INTEGER NOT NULL, "spotify_id" TEXT )')
        cur.execute('CREATE TABLE "users" ( "id" INTEGER, "name" TEXT NOT NULL, PRIMARY KEY("id" AUTOINCREMENT) )')

    logger.info("New database file created.")
