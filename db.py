#!/usr/local/bin/python3.11
import sqlite3 as sql
from datetime import datetime
from typing import Literal, Optional
from configparser import ConfigParser


'''
Note to anyone reading this. I'm aware the way I'm selecting the tables is bad!
I'll rewrite it using SQLAlchemy I swear
'''


# Note that SQLite can only work with dates in the YYYY-MM-DD format.

config = ConfigParser()
config.read("config.ini")
DATABASE = config["SETTINGS"]["DB_PATH"]


class Opener():
    def __init__(self, database):
        self.con = sql.connect(database)

    def __enter__(self):
        return self.con, self.con.cursor()

    def __exit__(self, type, value, traceback):
        self.con.commit()
        self.con.close()

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
def add_song(name : str, length : int, album : int, artist : str, spotify_id : Optional[int] = None) -> int:
    with Opener(DATABASE) as (con, cur):
        if spotify_id:
            cur.execute("INSERT INTO songs (name, length, album, artist, spotify_id) VALUES (?, ?, ?, ?, ?)", [name, length, album, artist, spotify_id])
        else:
            cur.execute("INSERT INTO songs (name, length, album, artist) VALUES (?, ?, ?, ?)", [name, length, album, artist])

    return cur.lastrowid



def get_id(table : Literal["artists", "albums", "songs", "playlists", "users"], name : str) -> int | None:
    with Opener(DATABASE) as (con, cur):
        cur.execute("SELECT * FROM '{}' WHERE name = ?".format(table), [name])
        results = cur.fetchall()

    if results:
        return results[0][0]
    return None

def insert(
    song : int,
    user : int,
    date : datetime
) -> None:
    with Opener(DATABASE) as (con, cur):
        date = date.strftime("%Y-%m-%d")

        cur.execute("INSERT INTO dated VALUES (?, ?, ?)", [song, user, date])



def update_time(
    old_row : list,
    new_time : int
) -> None:
    artist, album, song, time, user, date = old_row
    with Opener(DATABASE) as (con, cur):

        cur.execute("UPDATE dated SET time = ? WHERE (artist = ? AND album = ? AND song = ? AND user = ? AND date = ?)", [new_time, artist, album, song, user, date])



