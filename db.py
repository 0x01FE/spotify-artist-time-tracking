#!/usr/local/bin/python3.11

from typing import Literal, Optional
import sqlite3
import datetime
import configparser



'''
Note to anyone reading this. I'm aware the way I'm selecting the tables is bad!
I'll rewrite it using SQLAlchemy I swear
'''


# Note that SQLite can only work with dates in the YYYY-MM-DD format.

config = configparser.ConfigParser()
config.read("config.ini")
DATABASE = config["SETTINGS"]["DB_PATH"]


class Opener():
    def __init__(self, database):
        self.con = sqlite3.connect(database)

    def __enter__(self):
        return self.con, self.con.cursor()

    def __exit__(self, type, value, traceback):
        self.con.commit()
        self.con.close()


def get_latest_song_id() -> int:
    with Opener(DATABASE) as (con, cur):
        cur.execute("SELECT * FROM songs ORDER BY id DESC LIMIT 1")

        results = cur.fetchall()

    if not results:
        return 0
    else:
        return results[0][0]



def add_id(table : Literal["artists", "albums", "users"], name : str, spotify_id : Optional[str] = None) -> int:
    with Opener(DATABASE) as (con, cur):
        if spotify_id:
            cur.execute("INSERT INTO '{}' (name, spotify_id) VALUES (?, ?)".format(table), [name, spotify_id])
        else:
            cur.execute("INSERT INTO '{}' (name) VALUES (?)".format(table), [name])

    return cur.lastrowid


'''
Artist is a string with multiple id's if needed seperated by commas (ex: 1,2,3)

Returns song id
'''
def add_song(id : int, name : str, length : int, album : int, artist : str, spotify_id : Optional[int] = None) -> int:
    with Opener(DATABASE) as (con, cur):
        if spotify_id:
            cur.execute("INSERT INTO songs (id, name, length, album, artist, spotify_id) VALUES (?, ?, ?, ?, ?, ?)", [id, name, length, album, artist, spotify_id])
        else:
            cur.execute("INSERT INTO songs (id, name, length, album, artist) VALUES (?, ?, ?, ?, ?)", [id, name, length, album, artist])

    return cur.lastrowid



def get_id(table : Literal["albums", "songs", "playlists", "users"], name : str) -> int | None:
    with Opener(DATABASE) as (con, cur):
        cur.execute("SELECT * FROM '{}' WHERE name = ?".format(table), [name])
        results = cur.fetchall()

    if results:
        return results[0][0]
    return None

def get_song_id(song : str, artist_id : int) -> int | None:
    with Opener(DATABASE) as (con, cur):
        cur.execute("SELECT * FROM songs WHERE name = ? AND artist = ?", [song, artist_id])
        results = cur.fetchall()

    if results:
        return results[0][0]
    return None


def insert(
    song : int,
    user : int,
    date : datetime.datetime
) -> None:
    with Opener(DATABASE) as (con, cur):
        date = date.strftime("%Y-%m-%d")

        cur.execute("INSERT INTO dated VALUES (?, ?, ?)", [song, user, date])


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
