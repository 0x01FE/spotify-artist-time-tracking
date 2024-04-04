#!/usr/local/bin/python3.11

import os
import logging
import sqlite3
import datetime
import configparser

import sqlparse

from user import User

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
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class Opener():
    def __init__(self, database):
        self.con = sqlite3.connect(database)

    def __enter__(self):
        return self.con, self.con.cursor()

    def __exit__(self, type, value, traceback):
        self.con.commit()
        self.con.close()

SQL_DIR = "./sql/"
queries = {}
for sql_file in os.listdir(SQL_DIR):
    file_name = sql_file.split('.')[0]

    with open(SQL_DIR + sql_file, 'r') as file:
        raw_data = file.read()

    statements = sqlparse.split(raw_data)
    if len(statements) == 1:
        queries[file_name] = statements[0]
    else:
        queries[file_name] = statements


"""
Add an artist, album, or user to the database.

Parameters:
    table (Literal[str]) : Table that you are adding name to
    name (str) : Name of the item you are adding
    spotify_id (str | None) : spotify_id if this is hooked to spotify
        art_url (str) : art for album or artist icon

Returns:
    id (int) : Id of the added item
"""
def add_artist(name : str, spotify_id : str, icon_url : str) -> int:
    with Opener(DATABASE) as (con, cur):
        cur.execute(queries["insert_artist"], [name, spotify_id, icon_url])

    return cur.lastrowid


def add_album(name : str, spotify_id : str, cover_art_url : str) -> int:
    with Opener(DATABASE) as (con, cur):
        cur.execute(queries["insert_album"], [name, spotify_id, cover_art_url])

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
def add_song(id : int, name : str, length : int, album : int, artist : int, spotify_id : str | None = None) -> int:
    with Opener(DATABASE) as (con, cur):
        cur.execute(queries["insert_song"], [id, name, length, album, artist, spotify_id])

    return cur.lastrowid


"""
Get the id of some artist, album, or user.

Parameters:
    table (str) : Name of the table the item is in
    name (str) : Name of the item you're looking for

Returns:
    id (int | None) : Id if found, otherwise None.
"""
def get_artist_id(name : str) -> int | None:
    with Opener(DATABASE) as (con, cur):
        cur.execute(queries["get_artist_id"], [name])
        results = cur.fetchall()

    if results:
        return results[0][0]
    return None

def get_album_id(name : str) -> int | None:
    with Opener(DATABASE) as (con, cur):
        cur.execute(queries["get_album_id"], [name])
        results = cur.fetchall()

    if results:
        return results[0][0]
    return None

def get_user_id(name : str) -> int | None:
    with Opener(DATABASE) as (con, cur):
        cur.execute(queries["get_user_id"], [name])
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
def get_song_id(song_name : str, artist_id : int) -> int | None:
    with Opener(DATABASE) as (con, cur):
        cur.execute(queries["get_song_id"], [song_name, artist_id])
        results = cur.fetchall()

    if results:
        return results[0][0]
    return None


"""
Insert an event of a user listening to a song.

Parameters:
    song (int) : Id of the song in the event.
    date (datetime.datetime) : Datetime object representing the day of the event.
    time (int) : Amount of time the song was listened to.

Returns:
    None
"""
def insert(
    song : int,
    user : User,
    date : datetime.datetime,
    time : int,
    skip : bool
) -> None:
    with Opener(DATABASE) as (con, cur):
        date = date.strftime(DATE_FORMAT)

        cur.execute('INSERT INTO "listen-events" VALUES (?, ?, ?, ?, ?)', [song, user.id, date, time, skip])


"""
Get the latest song id.

Why:
    Some songs need to have the same id to support my system for handling a song with multiple artists.

Parameters:
    None

Returns:
    id (int) : latest id added
"""
def get_latest_song_id() -> int:
    with Opener(DATABASE) as (con, cur):
        cur.execute(queries["get_latest_song_id"])

        results = cur.fetchall()

    if not results:
        return 0
    else:
        return results[0][0]

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
        cur.execute('CREATE TABLE "listen-events" ( "song" INTEGER NOT NULL, "user" INTEGER NOT NULL, "date" TEXT NOT NULL, "time" INTEGER NOT NULL )')
        cur.execute('CREATE TABLE "songs" ( "id" INTEGER NOT NULL, "name" TEXT NOT NULL, "length" INTEGER NOT NULL, "album" INTEGER NOT NULL, "artist" INTEGER NOT NULL, "spotify_id" TEXT )')
        cur.execute('CREATE TABLE "users" ( "id" INTEGER, "name" TEXT NOT NULL, PRIMARY KEY("id" AUTOINCREMENT) )')

    logger.info("New database file created.")

def get_users() -> list[User] | None:
    with Opener(DATABASE) as (con, cur):
        cur.execute('SELECT * FROM users;')

        results = cur.fetchall()

    users = []
    for user in results:
        users.append(User(name=user[1]))

    return users

