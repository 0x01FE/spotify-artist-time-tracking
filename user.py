import json

import spotipy

from spotipy.oauth2 import SpotifyOAuth

import db



"""
Represents a user, their connection to the spotify api, and their connection to the database.
"""
class User():


    id : int
    name : str
    wait_time : int
    api : spotipy.Spotify


    def __init__(self, name : str):
        self.name = name
        self.wait_time = 0

        # Get Id or create Id
        results = self.get_id("users", self.name)

        if not results:
            with db.Opener(db.DATABASE) as (con, cur):
                cur.execute("INSERT INTO users (name) VALUES (?)", [self.name])

            self.id = self.get_id("users", self.name)
        else:
            self.id = results

        spotify_id = self.get_spotify_id()

        # Setup API connection
        with open(f"./data/.{spotify_id}-cache", 'r') as f:
            cache_data = json.loads(f.read())

        cache_handler = spotipy.MemoryCacheHandler(
            token_info=cache_data)

        self.api = spotipy.Spotify(
            auth_manager = SpotifyOAuth(
                scope=db.SCOPES,
                cache_handler=cache_handler
            ))

    def __str__(self) -> str:
        return self.name


    # Database Methods


    """
    Get the database id for this user.
    Really only meant as an internal method but no reason to mark it as such.

    Parameters:
        None
    Returns:
        id (str) : id of this user in the database
    """
    def get_spotify_id(self) -> str:
        with db.Opener(db.DATABASE) as (con, cur):
            cur.execute("SELECT * FROM users WHERE id = ?", [self.id, ])

            results = cur.fetchall()

        return results[0][2]