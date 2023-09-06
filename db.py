#!/usr/local/bin/python3.11
import sqlite3 as sql
from datetime import datetime
from typing import Literal, Optional

'''
Note to anyone reading this. I'm aware the way I'm selecting the tables is bad!
I'll rewrite it using SQLAlchemy I swear
'''


# Note that SQLite can only work with dates in the YYYY-MM-DD format.

db = './data/x.db'

class Opener():
    def __init__(self, database):
        self.con = sql.connect(database)

    def __enter__(self):
        return self.con, self.con.cursor()

    def __exit__(self, type, value, traceback):
        self.con.commit()
        self.con.close()

def add_id(table : Literal["artists", "albums", "songs", "playlists", "users"], name : str) -> int:
    with Opener(db) as (con, cur):
        cur.execute("INSERT INTO '{}' VALUES (?)".format(table), [name])

    return cur.lastrowid


def get_id(table : Literal["artists", "albums", "songs", "playlists", "users"], name : str) -> tuple[int, str, str | None]:
    with Opener(db) as (con, cur):
        cur.execute("SELECT * FROM '{}' WHERE name = ?".format(table), [name])
        results = cur.fetchall()

    return results

def insert(
    artist : int,
    album : int,
    song : int,
    time : int,
    user : int,
    date : Optional[datetime] = None
) -> None:
    with Opener(db) as (con, cur):

        if date:
            table = "dated"
            date = date.strftime("%Y-%m-%d")

            cur.execute("INSERT into '{}' VALUES (?, ?, ?, ?, ?, ?)".format(table), [artist, album, song, time, user, date])
        else:
            table = "overall"

            cur.execute("INSERT into '{}' VALUES (?, ?, ?, ?, ?)".format(table), [artist, album, song, time, user])



def update_time(
    old_row : list,
    new_time : int
) -> None:


    if len(old_row) == 6:
        artist, album, song, time, user, date = old_row
        with Opener(db) as (con, cur):

            cur.execute("UPDATE dated SET time = ? WHERE (artist = ? AND album = ? AND song = ? AND user = ? AND date = ?)", [new_time, artist, album, song, user, date])
    else:
        artist, album, song, time, user = old_row
        with Opener(db) as (con, cur):

            cur.execute("UPDATE overall SET time = ? WHERE (artist = ? AND album = ? AND song = ? AND user = ?)", [new_time, artist, album, song, user])



