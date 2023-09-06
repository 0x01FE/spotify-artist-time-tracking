import json
import sqlite3 as sql
from glob import glob
from datetime import datetime
import db

DATABASE = './data/jackson.db'
data_path = '/home/jackson/docker/volumes/spotify/jackson/'
USER = "jackson"


class Opener():
    def __init__(self):
        self.con = sql.connect(DATABASE)

    def __enter__(self):
        return self.con, self.con.cursor()

    def __exit__(self, type, value, traceback):
        self.con.commit()
        self.con.close()


def main() -> None:
    files = glob(data_path + "*.json")

    print('<' + '-'*50 + '>')
    print('Moving overall')

    with open(data_path + "overall.json", "r") as f:
        data = json.loads(f.read())

        for artist in data:
            print(f'moving artist {artist}')

            # Check if artist is in db
            with Opener() as (con, cur):
                cur.execute("SELECT * FROM artists WHERE name=:artist", {"artist" : artist})
                results = cur.fetchall()

                if not results:
                    cur.execute("INSERT INTO artists (name) VALUES (?)", [artist])

            for album in data[artist]["albums"]:

                # Check if ablum is in db
                with Opener() as (con, cur):
                    cur.execute("SELECT * FROM albums WHERE name=:album", {"album" : album})
                    results = cur.fetchall()

                    if not results:
                        cur.execute("INSERT INTO albums (name) VALUES (?)", [album])


                for song in data[artist]["albums"][album]["songs"]:

                    # Check if ablum is in db
                    with Opener() as (con, cur):
                        cur.execute("SELECT * FROM songs WHERE name=:song", {"song" : song})
                        results = cur.fetchall()

                        if not results:
                            cur.execute("INSERT INTO songs (name) VALUES (?)", [song])

                    # Get ids
                    artist_id = db.get_id("artists", artist)[0][0]
                    album_id = db.get_id("albums", album)[0][0]
                    song_id = db.get_id("songs", song)[0][0]
                    user_id = db.get_id("users", USER)[0][0]

                    time = data[artist]["albums"][album]["songs"][song]
                    db.insert(artist_id, album_id, song_id, time, user_id)


    print('<' + '-'*50 + '>')
    for day in files:
        if "overall" in day.split("/")[-1] or "last" in day.split("/")[-1]:
            continue

        print("Moving file " + day)

        with open(day, 'r') as f:
            data = json.loads(f.read())

        date = datetime.strptime(day.split("/")[-1][:10], "%d-%m-%Y")

        for artist in data:

            # Check if artist is in db
            with Opener() as (con, cur):
                cur.execute("SELECT * FROM artists WHERE name=:artist", {"artist" : artist})
                results = cur.fetchall()

                if not results:
                    cur.execute("INSERT INTO artists (name) VALUES (?)", [artist])

            for album in data[artist]["albums"]:

                # Check if ablum is in db
                with Opener() as (con, cur):
                    cur.execute("SELECT * FROM albums WHERE name=:album", {"album" : album})
                    results = cur.fetchall()

                    if not results:
                        cur.execute("INSERT INTO albums (name) VALUES (?)", [album])


                for song in data[artist]["albums"][album]["songs"]:

                    # Check if ablum is in db
                    with Opener() as (con, cur):
                        cur.execute("SELECT * FROM songs WHERE name=:song", {"song" : song})
                        results = cur.fetchall()

                        if not results:
                            cur.execute("INSERT INTO songs (name) VALUES (?)", [song])

                    # Get ids
                    artist_id = db.get_id("artists", artist)[0][0]
                    album_id = db.get_id("albums", album)[0][0]
                    song_id = db.get_id("songs", song)[0][0]
                    user_id = db.get_id("users", USER)[0][0]

                    time = data[artist]["albums"][album]["songs"][song]
                    db.insert(artist_id, album_id, song_id, time, user_id, date=date)




if __name__ == "__main__":
    # Make sure user exists
    results = db.get_id("users", "jackson")
    if not results:
        with Opener() as (con, cur):
            cur.execute("INSERT INTO users (name) VALUES (?)", ["jackson"])

    main()




